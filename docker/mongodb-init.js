// Indexes applied on first MongoDB container start.
db = db.getSiblingDB("tiktok_automator");

db.upload_jobs.createIndex(
  { post_id: 1, account_id: 1 },
  { unique: true, name: "upload_jobs_post_account_unique" }
);

db.upload_jobs.createIndex(
  { status: 1, retry_count: 1 },
  { name: "upload_jobs_status_retry" }
);

db.upload_jobs.createIndex(
  { "timing.completed_at": 1 },
  { expireAfterSeconds: 5184000, name: "upload_jobs_completed_ttl" }
);

db.accounts.createIndex({ status: 1 }, { name: "accounts_status" });
db.accounts.createIndex({ cooldown_until: 1 }, { name: "accounts_cooldown" });

db.posts.createIndex({ status: 1 }, { name: "posts_status" });
db.posts.createIndex({ "drive.file_id": 1 }, { unique: true, sparse: true, name: "posts_drive_file_unique" });

db.drive_sync_state.createIndex({ _id: 1 }, { name: "drive_sync_state_id" });
db.drive_pending_files.createIndex({ file_id: 1 }, { unique: true, name: "drive_pending_file_unique" });
db.drive_pending_files.createIndex(
  { first_seen_at: 1 },
  { expireAfterSeconds: 86400, name: "drive_pending_files_ttl" }
);

db.standby_proxies.createIndex({ status: 1 }, { name: "standby_proxies_status" });
db.standby_proxies.createIndex({ created_at: 1 }, { name: "standby_proxies_created_at" });
