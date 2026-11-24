const Redis = require("ioredis");
const redis = new Redis("redis://redis:6379");

const session = {
  internalUserId: "01a1f94a-71d0-743d-a8e5-74c456b01f70",
  courseId: "01a1f94a-71e6-7c70-97a8-eade510d71d2",
  role: "instructor",
  courseRole: "instructor",
  roles: ["Instructor"],
  lmsType: "canvas",
  lmsSub: "4d5925c8-d28b-4e23-96bf-27fb8024c388",
  displayName: "admin@canvas.local",
  email: "admin@canvas.local",
  lmsContextId: "canvas:1",
  loIds: [],
  chatbotEnabled: true,
  ttlSeconds: 86400
};

redis.set("session:lms:dev-session", JSON.stringify(session), "EX", 86400).then(() => {
  console.log("Redis session SET successfully with valid JSON");
  process.exit(0);
}).catch((err) => {
  console.error("Error setting session:", err);
  process.exit(1);
});
