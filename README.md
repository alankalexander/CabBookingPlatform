# 🚖 CabGo – Cab Booking Platform

**CabGo** is a full-stack cab booking application designed to make ride booking simple and convenient. It connects riders with drivers and provides an interactive map-based booking experience.

The application is developed using **Next.js, FastAPI, and PostgreSQL**, with separate frontend and backend modules.

## 🚀 Features

- **User Authentication** – Login and registration for riders and drivers.
- **Cab Booking** – Book rides by selecting pickup and destination locations.
- **Interactive Maps** – View pickup points, destinations, driver locations, and routes.
- **Driver Management** – Drivers can receive and accept ride requests.
- **Live Ride Status** – Track ride progress through different stages.
- **Fare Details** – View estimated and actual ride fares.
- **Payment Options** – Cash payment and online payment demonstration.
- **Payment Simulation** – Test successful and failed demo payments without real Razorpay credentials.
- **Ride Management** – Manage ride requests, cancellations, and completed rides.

## 🛠️ Technologies Used

### Frontend
- Next.js
- React.js
- JavaScript
- Tailwind CSS
- Leaflet / React-Leaflet

### Backend
- Python
- FastAPI
- SQLModel
- PostgreSQL
- Socket.IO

### Other Technologies
- OpenStreetMap
- OSRM Routing Service
- Razorpay integration (optional real-gateway configuration)
- Demo payment gateway

## 📁 Project Structure

```text
CabGo-Cab-Booking-Platform/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── auth.py
│   │   ├── payments.py
│   │   └── ...
│   ├── requirements.txt
│   └── ...
│
├── frontend/
│   ├── components/
│   ├── app/
│   ├── lib/
│   ├── package.json
│   └── ...
│
├── .gitignore
└── README.md
```

## ⚙️ Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/YOUR-USERNAME/CabGo-Cab-Booking-Platform.git
cd CabGo-Cab-Booking-Platform
```

### 2. Backend Setup

Open a terminal:

```bash
cd backend
python -m venv venv
```

Activate the virtual environment on Windows:

```powershell
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure your environment variables and PostgreSQL database using your local setup.

Start the backend:

```bash
python -m uvicorn app.main:asgi --reload --port 8000
```

Backend API documentation:

`http://127.0.0.1:8000/docs`

### 3. Frontend Setup

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the application:

`http://localhost:3000`

## 💳 Payment Information

CabGo supports cash payment and a simulated online payment experience.

The demo payment mode allows users to test:
- UPI payment simulation
- Card payment simulation
- Net banking simulation
- Successful payment
- Failed payment

**Note:** Demo payments do not process real transactions or charge actual money. Real Razorpay payments require valid API credentials and server-side verification.

## 🗺️ Map and Routing

CabGo uses OpenStreetMap-based mapping and OSRM routing to display routes between pickup and destination locations.

## 🔮 Future Improvements

- Production-ready payment gateway integration
- Improved live driver tracking
- Ride booking notifications
- Admin dashboard
- Deployment and cloud hosting

## 👨‍💻 Author

**Alan K Alexander**

Computer Science Engineering Graduate

GitHub: https://github.com/YOUR-USERNAME

---

⭐ If you find this project interesting, feel free to explore the repository and share your feedback.
