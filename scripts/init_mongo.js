// MongoDB Initialization Script
// Membuat indexes untuk koleksi ActivityLog dan CourseAnalytics

db = db.getSiblingDB('lms_analytics');

// ============================================================
// Collection: activity_logs
// ============================================================
db.createCollection('activity_logs');

db.activity_logs.createIndex({ "user_id": 1 });
db.activity_logs.createIndex({ "action": 1 });
db.activity_logs.createIndex({ "timestamp": -1 });
db.activity_logs.createIndex({ "user_id": 1, "timestamp": -1 });
db.activity_logs.createIndex({ "resource_type": 1, "resource_id": 1, "timestamp": -1 });

// TTL index: hapus log lama setelah 90 hari
db.activity_logs.createIndex(
    { "timestamp": 1 },
    { expireAfterSeconds: 7776000 }  // 90 days
);

print("✅ activity_logs indexes created");

// ============================================================
// Collection: learning_sessions
// ============================================================
db.createCollection('learning_sessions');

db.learning_sessions.createIndex({ "user_id": 1 });
db.learning_sessions.createIndex({ "course_id": 1 });
db.learning_sessions.createIndex({ "user_id": 1, "course_id": 1 });
db.learning_sessions.createIndex({ "started_at": -1 });

print("✅ learning_sessions indexes created");

// ============================================================
// Collection: course_analytics
// ============================================================
db.createCollection('course_analytics');

db.course_analytics.createIndex({ "course_id": 1 }, { unique: true });
db.course_analytics.createIndex({ "total_enrollments": -1 });
db.course_analytics.createIndex({ "completion_rate": -1 });

print("✅ course_analytics indexes created");

// ============================================================
// Collection: quiz_analytics
// ============================================================
db.createCollection('quiz_analytics');

db.quiz_analytics.createIndex({ "user_id": 1 });
db.quiz_analytics.createIndex({ "quiz_id": 1 });
db.quiz_analytics.createIndex({ "course_id": 1 });

print("✅ quiz_analytics indexes created");

print("🎉 MongoDB initialization complete!");
