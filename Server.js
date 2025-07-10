const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');

const app = express();
app.use(cors());
app.use(express.json());

// Connect to MongoDB Atlas
mongoose.connect("mongodb+srv://HARIHARAN:Hari0519@scms.wnt7tx1.mongodb.net/Attendance?retryWrites=true&w=majority&appName=SCMS", {
  useNewUrlParser: true,
  useUnifiedTopology: true
}).then(() => {
  console.log("✅ MongoDB connected successfully.");
}).catch(err => {
  console.error("❌ MongoDB connection error:", err);
});

// Define schema and model
const attendanceSchema = new mongoose.Schema({
  fingerId: Number,
  message: String,
  timestamp: { type: Date, default: Date.now }
});

const FingerAttendance = mongoose.model("Finger_Attendance", attendanceSchema);

// API endpoint to receive attendance data
app.post("/api/attendance", async (req, res) => {
  const { fingerId, message } = req.body;

  console.log(`📥 Received attendance data -> fingerId: ${fingerId}, message: "${message}"`);

  try {
    const entry = new FingerAttendance({ fingerId, message });
    await entry.save();
    console.log("✅ Attendance data saved to database:", entry);
    res.status(200).json({ success: true, data: entry });
  } catch (err) {
    console.error("❌ Failed to save attendance data:", err.message);
    res.status(500).json({ success: false, error: err.message });
  }
});

// Start server
const PORT = 8000;
app.listen(PORT, () => {
  console.log(`🚀 Server running on http://localhost:${PORT}`);
});
