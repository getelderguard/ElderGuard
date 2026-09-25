// Firestore rules tests. Run with `npm test` (starts the emulator) or, with the emulator already
// up on FIRESTORE_EMULATOR_HOST, `node --test`.
import { test, before, after, beforeEach } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  initializeTestEnvironment,
  assertSucceeds,
  assertFails,
} from "@firebase/rules-unit-testing";
import { doc, getDoc, setDoc, updateDoc, deleteDoc, serverTimestamp } from "firebase/firestore";

const PROJECT = "demo-elderguard";
const SENIOR = "uid-senior";
const GUARDIAN = "uid-guardian";
const STRANGER = "uid-stranger";
const ACCOUNT = SENIOR; // account id == senior uid

let env;

before(async () => {
  const [host, port] = (process.env.FIRESTORE_EMULATOR_HOST || "127.0.0.1:8080").split(":");
  env = await initializeTestEnvironment({
    projectId: PROJECT,
    firestore: {
      rules: readFileSync(new URL("../firestore.rules", import.meta.url), "utf8"),
      host,
      port: Number(port),
    },
  });
});

after(async () => {
  await env.cleanup();
});

beforeEach(async () => {
  await env.clearFirestore();
  await env.withSecurityRulesDisabled(async (ctx) => {
    const db = ctx.firestore();
    await setDoc(doc(db, "accounts", ACCOUNT), {
      senior: { uid: SENIOR, display_name: "Rosa", nickname: "Mom", phone_last4: "0142" },
      guardians: [{ uid: GUARDIAN, name: "J", relationship: "son" }],
      guardian_uids: [GUARDIAN],
      watch_list: [],
      settings: { announcement: true },
    });
    await setDoc(doc(db, "sessions", "s_1"), {
      account_id: ACCOUNT,
      state: "live",
      tier: "listening",
      transcript_stored: false,
    });
    await setDoc(doc(db, "phone_index", "abc123"), { account_id: ACCOUNT, role: "senior" });
    await setDoc(doc(db, "config", "flags"), { announcement: true });
    await setDoc(doc(db, "usage_events", "u1"), { capability: "scorer" });
  });
});

const as = (uid) => env.authenticatedContext(uid).firestore();
const anon = () => env.unauthenticatedContext().firestore();

test("senior reads own account", async () => {
  await assertSucceeds(getDoc(doc(as(SENIOR), "accounts", ACCOUNT)));
});

test("linked guardian reads the account", async () => {
  await assertSucceeds(getDoc(doc(as(GUARDIAN), "accounts", ACCOUNT)));
});

test("stranger and anonymous cannot read the account", async () => {
  await assertFails(getDoc(doc(as(STRANGER), "accounts", ACCOUNT)));
  await assertFails(getDoc(doc(anon(), "accounts", ACCOUNT)));
});

test("nobody writes accounts, not even the senior", async () => {
  await assertFails(updateDoc(doc(as(SENIOR), "accounts", ACCOUNT), { watch_list: ["x"] }));
  await assertFails(setDoc(doc(as(GUARDIAN), "accounts", "new"), { senior: {} }));
  await assertFails(deleteDoc(doc(as(SENIOR), "accounts", ACCOUNT)));
});

test("sessions readable by senior and guardian only", async () => {
  await assertSucceeds(getDoc(doc(as(SENIOR), "sessions", "s_1")));
  await assertSucceeds(getDoc(doc(as(GUARDIAN), "sessions", "s_1")));
  await assertFails(getDoc(doc(as(STRANGER), "sessions", "s_1")));
  await assertFails(getDoc(doc(anon(), "sessions", "s_1")));
  await assertFails(updateDoc(doc(as(SENIOR), "sessions", "s_1"), { tier: "stop" }));
});

test("owner writes a valid device doc", async () => {
  await assertSucceeds(
    setDoc(doc(as(SENIOR), "devices", SENIOR), {
      fcm_token: "tok-" + "a".repeat(40),
      platform: "ios",
      app_version: "1.0.0",
      updated_at: serverTimestamp(),
    }),
  );
  await assertSucceeds(getDoc(doc(as(SENIOR), "devices", SENIOR)));
  await assertSucceeds(deleteDoc(doc(as(SENIOR), "devices", SENIOR)));
});

test("device doc rejects bad schema and other users", async () => {
  const good = {
    fcm_token: "tok",
    platform: "android",
    app_version: "1.0.0",
    updated_at: serverTimestamp(),
  };
  await assertFails(setDoc(doc(as(SENIOR), "devices", SENIOR), { ...good, platform: "web" }));
  await assertFails(setDoc(doc(as(SENIOR), "devices", SENIOR), { ...good, fcm_token: "x".repeat(513) }));
  await assertFails(setDoc(doc(as(SENIOR), "devices", SENIOR), { ...good, extra: 1 }));
  await assertFails(setDoc(doc(as(SENIOR), "devices", SENIOR), { ...good, updated_at: 123 }));
  await assertFails(setDoc(doc(as(STRANGER), "devices", SENIOR), good));
  await assertFails(getDoc(doc(as(STRANGER), "devices", SENIOR)));
});

test("server-only collections are unreadable", async () => {
  for (const [coll, id] of [
    ["phone_index", "abc123"],
    ["config", "flags"],
    ["usage_events", "u1"],
  ]) {
    await assertFails(getDoc(doc(as(SENIOR), coll, id)));
    await assertFails(getDoc(doc(as(GUARDIAN), coll, id)));
    await assertFails(setDoc(doc(as(SENIOR), coll, id), { x: 1 }));
  }
});
