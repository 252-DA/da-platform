#!/usr/bin/env python3
"""Live Canvas → web → core-api → Redis → worker/LLM → Canvas smoke test.

Run from the platform checkout: python3 scripts/test_essay_grading.py [--keep]
Requires the development Docker stack and its registered Canvas LTI tool.
Uses the configured judge (real API usage), creates a separate test course,
and removes its fixtures unless --keep is given. No existing submissions change.
"""

import argparse
import json
import subprocess
import sys
import time
import uuid


MARKER = "ESSAY_SMOKE_JSON="


def run(container, command, source, data, timeout=90):
    result = subprocess.run(
        ["docker", "exec", "-i", "-e", f"ESSAY_SMOKE_DATA={json.dumps(data)}",
         container, *command],
        input=source, text=True, capture_output=True, timeout=timeout,
    )
    if result.returncode:
        raise RuntimeError(f"{container}: {(result.stderr or result.stdout)[-2500:]}")
    for line in reversed(result.stdout.splitlines()):
        if line.startswith(MARKER):
            return json.loads(line[len(MARKER):])
    raise RuntimeError(f"{container}: missing test result: {result.stdout[-1000:]}")


CANVAS = r'''
require "json"
require "stringio"
require "uri"
d = JSON.parse(ENV.fetch("ESSAY_SMOKE_DATA"))
out = case d.fetch("action")
when "preflight"
  tool = ContextExternalTool.active.detect { |t| t.global_developer_key_id.to_s == d.fetch("clientId") }
  raise "LTI tool not found" unless tool
  scopes = %w[noticehandlers asset.readonly report].map { |s| "https://purl.imsglobal.org/spec/lti/scope/#{s}" }
  raise "Missing LTI scopes: #{scopes - tool.developer_key.scopes}" unless (scopes - tool.developer_key.scopes).empty?
  raise "Document Processor feature is disabled" unless tool.root_account.feature_enabled?(:lti_asset_processor)
  raise "ActivityAssetProcessor placement is disabled" unless tool.extension_setting("ActivityAssetProcessor", :enabled)
  base = URI(tool.url)
  handler_url = "#{base.scheme}://#{base.host}#{base.port == base.default_port ? '' : ":#{base.port}"}/api/lti/notices"
  handlers = tool.lti_notice_handlers.active.where(notice_type: "LtiAssetProcessorSubmissionNotice")
  raise "Existing handler belongs to another app; refusing to replace it" if handlers.any? { |h| h.url != handler_url }
  {toolId: tool.id, handlerUrl: handler_url, handlerIds: handlers.pluck(:id),
   handlerMaxBatchSize: handlers.first&.max_batch_size,
   pnsUrl: Rails.application.routes.url_helpers.update_lti_notice_handlers_url(
     context_external_tool_id: tool.id, host: tool.root_account.environment_specific_domain,
     protocol: URI(d.fetch("platform")).scheme)}
when "seed"
  ActiveRecord::Base.transaction do
    course = Account.default.courses.create!(name: "DA essay grading smoke #{d.fetch('runId')}",
      course_code: d.fetch("runId"), workflow_state: "available")
    teacher = User.create!(name: "Essay smoke teacher #{d.fetch('runId')}")
    student = User.create!(name: "Essay smoke student #{d.fetch('runId')}")
    course.enroll_teacher(teacher, enrollment_state: "active")
    course.enroll_student(student, enrollment_state: "active")
    {canvasCourseId: course.id, contextId: Lti::V1p1::Asset.opaque_identifier_for(course),
     teacherId: teacher.id, teacherSub: teacher.lti_id, studentId: student.id, studentSub: student.lti_id}
  end
when "submit"
  course = Course.find(d.fetch("canvasCourseId"))
  student = User.find(d.fetch("studentId"))
  assignment = course.assignments.create!(title: "Essay smoke #{d.fetch('extension')}",
    submission_types: "online_upload", points_possible: 10, workflow_state: "published")
  tool = ContextExternalTool.find(d.fetch("toolId"))
  app_url = d.fetch("handlerUrl").delete_suffix("/api/lti/notices")
  processor = assignment.lti_asset_processors.create!(context_external_tool: tool,
    title: "DA essay smoke", url: "#{app_url}/lti/asset-processor",
    custom: {"da_processor_id" => d.fetch("processorId")}, report: {"url" => "#{app_url}/lti/essay-report"})
  attachment = Attachment.create!(context: student, user: student,
    filename: "essay-smoke.#{d.fetch('extension')}", display_name: "essay-smoke.#{d.fetch('extension')}",
    content_type: d.fetch("contentType"), uploaded_data: StringIO.new(d.fetch("content")))
  # The normal submission method triggers AssetProcessorNotifier and Canvas PNS.
  submission = assignment.submit_homework(student, submission_type: "online_upload", attachments: [attachment])
  {assignmentId: assignment.id, submissionId: submission.id, submissionLtiId: submission.lti_attempt_id,
   canvasProcessorId: processor.id, attachmentId: attachment.id}
when "report"
  submission = Submission.find(d.fetch("submissionId"))
  reports = Lti::AssetReport.active.where(lti_asset_processor_id: d.fetch("canvasProcessorId"))
  {grade: submission.grade, score: submission.score, reports: reports.map { |r|
    {progress: r.processing_progress, result: r.result, errorCode: r.error_code, comment: r.comment}
  }}
when "cleanup"
  if d["canvasCourseId"]
    course = Course.find(d.fetch("canvasCourseId"))
    raise "Refusing to remove a non-test course" unless course.course_code == d.fetch("runId")
    course.destroy
    [d["teacherId"], d["studentId"]].compact.each { |id| User.find(id).destroy }
  end
  tool = ContextExternalTool.find(d.fetch("toolId"))
  tool.lti_notice_handlers.active.where(notice_type: "LtiAssetProcessorSubmissionNotice", url: d.fetch("handlerUrl"))
    .where.not(id: d.fetch("handlerIds")).each(&:destroy)
  unless d.fetch("handlerIds").empty? || tool.lti_notice_handlers.active.where(id: d.fetch("handlerIds")).exists?
    Lti::PlatformNotificationService.subscribe_tool_for_notice(tool: tool,
      notice_type: "LtiAssetProcessorSubmissionNotice", handler_url: d.fetch("handlerUrl"),
      max_batch_size: d["handlerMaxBatchSize"])
  end
  {cleaned: true}
else
  raise "Unknown action"
end
puts "ESSAY_SMOKE_JSON=#{out.to_json}"
'''


CORE = r'''
const {Client} = require('pg');
const crypto = require('node:crypto');
const d = JSON.parse(process.env.ESSAY_SMOKE_DATA);
async function main() {
  if (d.action === 'config') return {clientId: process.env.LTI_CLIENT_ID, platform: process.env.LTI_PLATFORM_URL};
  const db = new Client({connectionString: process.env.DATABASE_URL});
  await db.connect();
  try {
    if (d.action === 'seed') {
      await db.query('BEGIN');
      const courseId = crypto.randomUUID(), teacherId = crypto.randomUUID(), studentId = crypto.randomUUID();
      await db.query('INSERT INTO courses (course_id,lms_id,code,name) VALUES ($1,$2,$3,$4)',
        [courseId, `canvas:${d.contextId}`, d.runId, `Essay grading smoke ${d.runId}`]);
      for (const [id, sub, role] of [[teacherId,d.teacherSub,'instructor'],[studentId,d.studentSub,'learner']]) {
        await db.query('INSERT INTO lms_user_mappings (internal_user_id,lms_type,lms_sub,display_name,role) VALUES ($1,$2,$3,$4,$5)',
          [id,'canvas',sub,`Essay smoke ${role} ${d.runId}`,role]);
        await db.query('INSERT INTO course_memberships (user_id,course_id,role) VALUES ($1,$2,$3)', [id,courseId,role]);
      }
      await db.query('COMMIT');
      return {courseId,internalTeacherId:teacherId,internalStudentId:studentId};
    }
    if (d.action === 'state') {
      const rows = (await db.query(`SELECT s.essay_submission_id, s.status, s.result, s.error_code, s.error,
        s.attempts, s.assets, s.reported_at FROM essay_submissions s JOIN essay_processors p USING (processor_id)
        WHERE p.course_id=$1 AND s.lms_submission_id=$2 ORDER BY s.received_at`, [d.courseId,d.submissionLtiId])).rows;
      return {rows};
    }
    if (d.action === 'cleanup') {
      const course = (await db.query('SELECT code FROM courses WHERE course_id=$1', [d.courseId])).rows[0];
      if (!course || course.code !== d.runId) throw Error('Refusing to remove a non-test course');
      const assets = (await db.query(`SELECT s.assets FROM essay_submissions s JOIN essay_processors p USING (processor_id)
        WHERE p.course_id=$1`, [d.courseId])).rows.flatMap(r => r.assets);
      const {Client:Minio} = require('minio');
      const [host,port] = (process.env.MINIO__ENDPOINT || 'minio:9000').split(':');
      const storage = new Minio({endPoint:host,port:Number(port || 9000),useSSL:process.env.MINIO__SECURE === 'true',
        accessKey:process.env.MINIO__ACCESS_KEY,secretKey:process.env.MINIO__SECRET_KEY});
      for (const a of assets) if (a.storage_key) await storage.removeObject(process.env.MINIO__BUCKET_NAME || 'documents',a.storage_key);
      await db.query('BEGIN');
      await db.query(`DELETE FROM outbox_events WHERE event_type='ESSAY_GRADING_REQUESTED' AND payload->>'course_id'=$1`,[d.courseId]);
      await db.query('DELETE FROM essay_processors WHERE course_id=$1',[d.courseId]);
      await db.query('DELETE FROM llm_usage_logs WHERE course_id=$1',[d.courseId]);
      await db.query('DELETE FROM course_memberships WHERE course_id=$1',[d.courseId]);
      await db.query('DELETE FROM courses WHERE course_id=$1',[d.courseId]);
      await db.query('DELETE FROM lms_user_mappings WHERE internal_user_id=ANY($1::uuid[])',[[d.internalTeacherId,d.internalStudentId]]);
      await db.query('COMMIT');
      return {cleaned:true};
    }
    throw Error('Unknown action');
  } finally { await db.end(); }
}
main().then(out => console.log('ESSAY_SMOKE_JSON='+JSON.stringify(out))).catch(e => {console.error(e.message);process.exitCode=1});
'''


WEB = r'''
const fs = require('node:fs');
const crypto = require('node:crypto');
const grpc = require('@grpc/grpc-js');
const loader = require('@grpc/proto-loader');
const d = JSON.parse(process.env.ESSAY_SMOKE_DATA);
const definition = loader.loadSync('/app/proto/core_api.proto', {keepCase:false,defaults:true});
const Api = grpc.loadPackageDefinition(definition).ai_lms.v1.CoreApiService;
const client = new Api(process.env.CORE_API_GRPC_HOST || 'core-api:50051',grpc.credentials.createInsecure());
const now = Math.floor(Date.now()/1000);
const encode = v => Buffer.from(JSON.stringify(v)).toString('base64url');
const header = encode({alg:'EdDSA',kid:process.env.BFF_TO_CORE_KEY_ID});
const payload = encode({iss:process.env.BFF_TO_CORE_JWT_ISSUER || 'web-bff',
  aud:process.env.BFF_TO_CORE_JWT_AUDIENCE || 'core-api',sub:d.internalTeacherId,scope:'course',
  courseId:d.courseId,roles:['instructor'],jti:crypto.randomUUID(),iat:now,exp:now+60});
const signed = header+'.'+payload;
const signature = crypto.sign(null,Buffer.from(signed),fs.readFileSync(process.env.BFF_TO_CORE_PRIVATE_KEY_PATH)).toString('base64url');
const metadata = new grpc.Metadata();
metadata.set('authorization','Bearer '+signed+'.'+signature);
client[d.method]({json:JSON.stringify(d.body)},metadata,{deadline:Date.now()+60000},(err,res) => {
  client.close();
  if (err) {console.error(err.message);process.exitCode=1;return;}
  console.log('ESSAY_SMOKE_JSON='+JSON.stringify(JSON.parse(res.json)));
});
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep", action="store_true", help="Keep test course, submissions and reports for inspection")
    parser.add_argument("--timeout", type=int, default=240, help="Seconds to wait for each report (default: 240)")
    args = parser.parse_args()
    data = {"runId": f"essay-smoke-{uuid.uuid4().hex[:12]}"}

    def canvas(action):
        return run("canvas-lms-web-1", ["bundle", "exec", "rails", "runner", "-"], CANVAS, {**data, "action": action})

    def core(action):
        return run("da-platform-core-api-1", ["node"], CORE, {**data, "action": action})

    try:
        data.update(core("config"))
        data.update(canvas("preflight"))
        data.update(canvas("seed"))
        data.update(core("seed"))
        print(f"Created isolated test course: {data['runId']}", flush=True)
        processor = run("da-platform-web-1", ["node"], WEB, {**data, "method": "CreateEssayProcessor", "body": {
            "courseId": data["courseId"], "title": "Essay smoke: Lambda architecture",
            "instructions": "Explain the batch, speed and serving layers of Lambda architecture and one tradeoff.",
            "rubric": [
                {"criterion": "Three layers", "description": "Explain the roles of batch, speed and serving layers", "points": 6},
                {"criterion": "Tradeoff", "description": "State a meaningful benefit and limitation", "points": 4},
            ], "visibleToOwner": True, "pnsUrl": data["pnsUrl"], "handlerUrl": data["handlerUrl"],
        }})
        data["processorId"] = processor["processor_id"]
        for extension, content_type, content, expected in [
            ("txt", "text/plain", "Lambda architecture uses a batch layer to store immutable historical data and recompute accurate views. "
             "The speed layer processes new events with low latency until the batch catches up. The serving layer exposes indexed batch views, "
             "and queries combine batch and real-time results. This balances correctness and freshness, but maintaining two processing paths adds complexity.", "REPORTED"),
            ("zip", "application/zip", "PK unsupported file smoke test", "FAILED"),
        ]:
            data.update(extension=extension, contentType=content_type, content=content)
            data.update(canvas("submit"))
            print(f"Submitted .{extension}: assignment {data['assignmentId']}", flush=True)
            deadline = time.monotonic() + args.timeout
            last_status = None
            row = None
            while time.monotonic() < deadline:
                rows = core("state")["rows"]
                row = rows[-1] if rows else None
                status = row["status"] if row else "WAITING_FOR_NOTICE"
                if status != last_status:
                    print(f"  {status}", flush=True)
                    last_status = status
                if row and row["reported_at"]:
                    break
                time.sleep(3)
            else:
                raise RuntimeError(f"Timed out: {json.dumps(row, ensure_ascii=False)}")
            if row["status"] != expected:
                raise AssertionError(f"Expected {expected}: {json.dumps(row, ensure_ascii=False)}")
            report = canvas("report")
            if report["grade"] is not None or report["score"] is not None:
                raise AssertionError("AI wrote an official Canvas grade instead of a suggested report")
            if len(report["reports"]) != 1:
                raise AssertionError(f"Expected one Canvas asset report: {report}")
            received = report["reports"][0]
            if expected == "REPORTED":
                result = row["result"]
                criteria = result["criteria"]
                if len(criteria) != 2 or result["max_score"] != 10 or not 0 <= result["score"] <= 10:
                    raise AssertionError(f"Invalid rubric result: {result}")
                if any(not 0 <= c["points"] <= c["max_points"] for c in criteria):
                    raise AssertionError(f"Criterion score out of range: {result}")
                if abs(sum(c["points"] for c in criteria) - result["score"]) > 0.001:
                    raise AssertionError(f"Criterion scores do not sum to total: {result}")
                if received["progress"] != "Processed" or received["result"] != f"{result['score']:g}/10":
                    raise AssertionError(f"Canvas report differs from worker result: {report}")
                detail = run("da-platform-web-1", ["node"], WEB, {**data, "method": "GetEssayReport", "body": {
                    "submissionId": data["submissionLtiId"], "userSub": data["studentSub"],
                }})
                if len(detail) != 1 or detail[0]["result"] != result or not detail[0]["is_teacher"]:
                    raise AssertionError(f"Report detail API differs from worker result: {detail}")
                print(f"PASS .txt: {received['result']}, model={result['model']}, rubric and Canvas report agree", flush=True)
            elif row["error_code"] != "UNSUPPORTED_ASSET_TYPE" or received["progress"] != "Failed" or received["errorCode"] != row["error_code"]:
                raise AssertionError(f"Unsupported file did not produce the expected error: {row}, {report}")
            else:
                print("PASS .zip: UNSUPPORTED_ASSET_TYPE reported to Canvas", flush=True)
            if args.keep:
                print(f"  SpeedGrader: {data['platform']}/courses/{data['canvasCourseId']}/gradebook/speed_grader"
                      f"?assignment_id={data['assignmentId']}&student_id={data['studentId']}", flush=True)
        print("PASS: live file grading, failure report, and official grade unchanged.", flush=True)
    finally:
        if args.keep and data.get("canvasCourseId"):
            print(f"Kept test course: {data['platform']}/courses/{data['canvasCourseId']}", flush=True)
        else:
            errors = []
            for cleanup in ([lambda: core("cleanup")] if data.get("courseId") else []) + ([lambda: canvas("cleanup")] if data.get("toolId") else []):
                try:
                    cleanup()
                except Exception as exc:
                    errors.append(str(exc))
            if errors:
                raise RuntimeError("Test fixture cleanup failed: " + "; ".join(errors))
            if data.get("canvasCourseId"):
                print("Removed test fixtures and restored the notice handler configuration.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
