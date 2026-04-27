# 🔐 Secure Document Verification Platform  

### 📄 Microservices-Based Architecture for Document Verification & Similarity Detection

---

## 📌 Overview

This repository contains a **Secure Document Verification Platform** developed using **Microservices Architecture** for validating uploaded documents, detecting duplicate/similar content, and generating verification reports.

The system is designed for **academic institutions, enterprises, and digital governance platforms** requiring secure and scalable document authentication.

---

## 🎯 Objectives

• Secure document upload and storage  
• Detect duplicate / plagiarized content  
• Generate automated verification reports  
• JWT-based secure authentication  
• Scalable distributed deployment using Docker  
• Modular microservices communication via REST APIs  

---

## 🛠️ Tech Stack

### 💻 Backend
• Python 🐍  
• FastAPI ⚡  

### 🗄️ Database
• MySQL 🐬  

### 🔐 Security
• JWT Authentication 🔑  

### 🤖 Similarity Detection
• TF-IDF Vectorization 📊  
• Cosine Similarity 📐  
• Scikit-learn 🧠  

### 🐳 Deployment
• Docker  
• Docker Compose  

### 🎨 Frontend
• React.js ⚛️  
• HTML  
• CSS  
• JavaScript  

---

## 📂 Project Structure

```text
**Secure-Document-Platform/**
│
├── api-gateway/             
├── auth-service/           
├── document-service/       
├── report-service/         
├── secure-doc-frontend/ 
🧩 Microservices Modules

🌐** API Gateway**

• Main entry point for all requests
• Request routing
• Load balancing ready
• Token validation
• Communication control

🔑 **Auth Service**

• User registration
• Login authentication
• JWT token generation
• Authorization

📁 **Document Service**

• Upload documents
• Store metadata
• Maintain records
• Manage user files

🧠 **Similarity Detection Engine**

• TF-IDF Vectorization
• Cosine Similarity
• Duplicate detection
• Modified copy detection

📊** Report Service**

• Similarity score report
• Verification status
• PDF report generation
• Final summary

🔄 **Workflow**

👤 User Uploads File
        ↓
🌐 API Gateway
        ↓
🔑 Auth Validation
        ↓
📁 Document Storage
        ↓
🧠 Similarity Analysis
        ↓
📊 Verification Report
        ↓
✅ Result to User


**🏗️ System Architecture**

User
 ↓
API Gateway
 ↓
---------------------------------
| 🔑 Auth Service              |
| 📁 Document Service          |
| 🧠 Similarity Service        |
| 📊 Report Service            |
---------------------------------
 ↓
🗄️ MySQL Database
🤖 Similarity Detection Logic

📌 **TF-IDF**
• Converts document text into vectors based on word importance.

📌 **Cosine Similarity**
• Measures similarity between vectors.

**Score	Result**

1.00	Exact Match 🔴
0.85	High Similarity 🟠
0.55	Medium Similarity 🟡
0.12	Unique Document 🟢

📈 Performance Results

**Metric**	          **  Result**
⚡ API Response Time	    120 ms
📄 Document Processing	  1.8 sec
🤖 Similarity Detection	  0.9 sec
👥 Concurrent Users      	50+

🌐 API Gateway	      5%	    120 MB
🔑 Auth Service	      8%	    150 MB
📁 Document Service	  12%	    220 MB
🧠 Similarity Service	18%	    300 MB


**▶️ How to Run**

Clone Repository
git clone https://github.com/Kishore-B06/Secure-Document-Platform.git
Enter Project
cd Secure-Document-Platform
Start Backend Services
docker-compose up --build
Run Frontend
cd secure-doc-frontend
npm install
npm start

**🔐 Security Features**

• JWT Authentication
• Protected APIs
• Secure token access
• Container isolation
• Role-based access ready

**🚀 Future Enhancements**

• Blockchain verification
• AI-based fraud detection
• OCR for scanned documents
• AWS / Azure deployment
• LLM semantic similarity
• Mobile app integration


**📚 Research Paper Basis**

**Secure Document Verification Platform: A Microservices-Based Architecture for Document Verification and Similarity Detection**

**Authors:**
• Kishore B
• Praveen Kanth N
• Jaya Kumar H S

🎓 VIT University, Vellore


**🤝 Contributing**

• Fork repository
• Improve features
• Enhance UI
• Optimize scalability

**📜 License**

For educational and research purposes.

**👤 Author**

Kishore B
VIT University, Vellore

**⭐ Acknowledgement**

• Faculty mentors
• VIT University
• FastAPI community
• Docker community
• Open-source contributors
