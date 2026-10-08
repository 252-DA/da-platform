// Generate the local key pairs that web and core-api read at startup.
// A pair is skipped if either file already exists, so working keys are never
// replaced; delete both files of a pair to regenerate it.
//
//   web/keys/lti.pem + lti.pub.pem      RS256: LTI deep-link and AGS token JWTs.
//                                        Canvas reads the public half from the
//                                        tool's /.well-known/jwks.json.
//   web/keys/bff-to-core.pem
//   + core-api/keys/bff-to-core.pub.pem EdDSA (Ed25519): web -> core-api JWTs.
//
// Node instead of openssl: the macOS openssl (LibreSSL) cannot make Ed25519 keys.
// Usage: node scripts/gen_dev_keys.mjs
import { generateKeyPairSync } from 'node:crypto';
import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const pem = {
  privateKeyEncoding: { type: 'pkcs8', format: 'pem' },
  publicKeyEncoding: { type: 'spki', format: 'pem' },
};

const pairs = [
  { type: 'rsa', options: { modulusLength: 2048 }, privatePath: 'web/keys/lti.pem', publicPath: 'web/keys/lti.pub.pem' },
  { type: 'ed25519', options: {}, privatePath: 'web/keys/bff-to-core.pem', publicPath: 'core-api/keys/bff-to-core.pub.pem' },
];

for (const { type, options, privatePath, publicPath } of pairs) {
  const [privateFile, publicFile] = [privatePath, publicPath].map((p) => join(root, p));
  if (existsSync(privateFile) || existsSync(publicFile)) {
    console.log(`skip    ${privatePath}: already exists`);
    continue;
  }
  const { privateKey, publicKey } = generateKeyPairSync(type, { ...options, ...pem });
  mkdirSync(dirname(privateFile), { recursive: true });
  mkdirSync(dirname(publicFile), { recursive: true });
  writeFileSync(privateFile, privateKey, { mode: 0o600 });
  writeFileSync(publicFile, publicKey, { mode: 0o644 });
  console.log(`created ${privatePath} + ${publicPath}`);
}
