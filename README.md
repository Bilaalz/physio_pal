# 🤖 PhysioPal: AI-Powered Exercise Analysis & Physiotherapy Assistant

> Bringing professional physiotherapy guidance directly to your home through AI-powered exercise analysis.

[🎥 Watch Demo on YouTube](https://www.youtube.com/watch?v=iDiVruzdzFk) | [🚀 View on Devpost](https://devpost.com/software/physiopal-w89i2z?ref_content=user-portfolio&ref_feature=in_progress#references)

---

## 📖 Overview
PhysioPal is an AI-powered physiotherapy assistant that analyzes your exercise form in real time using just a webcam. It provides **instant feedback**, **rep counting**, and **form correction cues**, bridging the gap between professional guidance and home-based rehabilitation.

---

## 🎯 Problem & Background
Canada faces a **physiotherapy workforce crisis**, requiring a **62% increase in physiotherapists** just to meet the OECD average of 1.1 per 1,000 population.  
This shortage limits access to supervised rehabilitation, especially in remote or underserved regions.  

Meanwhile, most fitness apps focus on **rep counting or tracking**, but **lack quality-of-movement analysis** — leaving users prone to injury and ineffective training.

> PhysioPal addresses this by turning everyday devices into digital physiotherapists that guide, monitor, and correct users during exercises in real time.

---

## 💡 Motivation
Many people want to recover from injury or stay active, but lack consistent, affordable coaching.  
PhysioPal helps users:
- Exercise safely with **AI-based posture correction**
- Build confidence and track progress
- Access guided rehabilitation **anytime, anywhere**

---

## ✨ Inspiration
The idea came from watching friends and family struggle through rehabilitation without consistent physiotherapy access.  
With computer vision technologies like **MediaPipe** and **OpenPose**, it became clear that AI could **bring expert-level feedback to home environments**.

> The vision: democratize physiotherapy through intelligent, accessible AI.

---

## 🧠 What I Learned

### 🧩 Technical Skills
- **Computer Vision & Pose Estimation:** Extracted 33 body keypoints via MediaPipe and computed joint angles for biomechanical feedback  
- **Real-Time Video Processing:** Built efficient pipelines with OpenCV and Streamlit (WebRTC integration for live webcam streaming)  
- **State Machine Design:** Tracked complex movement sequences to ensure accurate repetition detection  
- **AI Integration:** Experimented with Google Gemini API for personalized exercise guidance and chatbot interaction  
- **Web Development:** Designed a multi-page Streamlit interface with responsive layout and video overlays  

### 🩺 Domain Knowledge
- **Biomechanics:** Learned about joint kinematics and how to compute meaningful movement metrics  
- **Physiotherapy Principles:** Studied injury prevention, safe progression, and corrective feedback  
- **Healthcare Accessibility:** Explored the Canadian physiotherapy shortage and its systemic impact  

---

## 🧰 Tech Stack

| Category | Tools / Libraries |
|-----------|------------------|
| **Languages** | Python |
| **Frameworks** | Streamlit |
| **Computer Vision** | MediaPipe, OpenCV, NumPy |
| **AI & APIs** | Google Gemini API |
| **Video & Web** | WebRTC, Streamlit Cloud |
| **Version Control** | Git, GitHub |

---

## ⚙️ How It Works
1. User starts webcam feed through Streamlit  
2. MediaPipe detects 33 body landmarks in real time  
3. Angles and motion states are calculated for each repetition  
4. PhysioPal provides instant feedback such as:
   - ✅ Correct form  
   - ⚠️ Knee too forward  
   - 🔁 Repeat the motion  

---

## 🏗️ Future Improvements
- 🧍‍♂️ Multi-exercise support with dynamic detection  
- 📈 Progress tracking dashboards  
- 🔊 Real-time voice feedback using ElevenLabs  
- ☁️ Cloud-based analytics and exercise history  

---

## 📜 License
This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 🙌 Acknowledgements
- Google MediaPipe Team  
- Streamlit Community  
- OpenCV Contributors  
- Physiotherapy professionals who shared insight during testing  

---

### 🔗 References
[1] Canadian Institute for Health Information, 2024 – *“Physiotherapist Workforce Shortage in Canada”*
