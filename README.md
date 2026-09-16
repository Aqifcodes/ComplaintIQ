# ComplaintIQ

AI-powered complaint management platform that helps organizations classify, prioritize, and resolve customer complaints through an intelligent customer–admin workflow.

> ComplaintIQ combines machine learning and generative AI to turn unstructured complaints into actionable information for management.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [How It Works](#how-it-works)
- [AI Prediction Flow](#ai-prediction-flow)
- [Privacy and PII Protection](#privacy-and-pii-protection)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Application Workflow](#application-workflow)
- [Prediction Transparency](#prediction-transparency)
- [Database](#database)
- [UI and UX](#ui-and-ux)
- [Security Considerations](#security-considerations)
- [Limitations](#limitations)
- [Future Improvements](#future-improvements)
- [Project Status](#project-status)
- [Author](#author)
- [Acknowledgements](#acknowledgements)
- [Disclaimer](#disclaimer)

---

## Overview

Traditional complaint systems mainly store complaints and allow administrators to respond manually.

ComplaintIQ adds an intelligence layer to that workflow. When a customer submits a complaint, the system automatically analyzes it and predicts:

- Complaint category
- Complaint priority
- Prediction confidence
- Prediction source

The complaint is then available to administrators through an admin dashboard, where they can review the original complaint, inspect the AI predictions, respond to the customer, and resolve the complaint.

Customers can track their submitted complaints and view administrator responses directly from the platform.

---

## Key Features

### Customer Portal

- Secure customer login
- Submit complaints with title and description
- View previously submitted complaints
- Open individual complaint details
- View administrator responses
- Track complaint status
- Resolved complaints are clearly highlighted
- Light and dark mode with persistent theme preference via `localStorage`

### AI Complaint Classification

- Random Forest-based complaint classification
- Confidence score for category prediction
- Low-confidence predictions are passed to Gemini as a fallback
- Gemini can identify existing categories or suggest a new one
- New categories can be evaluated before being promoted into the system

### AI Priority Classification

- Complaint priority prediction constrained to the application's official priority values
- Gemini is used when the primary model is uncertain
- Priority prediction includes a confidence value
- Prediction source is stored separately

### Privacy Protection

- PII masking applied before complaint text is sent to Gemini
- Sensitive information is removed or masked before external AI processing
- Original complaint information remains available within the application

### Admin Dashboard

- View all complaints
- Filter by category, priority, and status
- View complaint details including AI predictions and confidence scores
- See which model produced each prediction
- Respond directly to customers
- Resolve complaints through the response workflow
- Override incorrect AI-predicted category or priority directly from the complaint detail page 

### Complaint Status

ComplaintIQ uses two customer-facing complaint states:

- `Awaiting Response`
- `Resolved`

When an administrator submits a response, the complaint is automatically marked as resolved.

---

## How It Works

```text
Customer
   │
   │ Submit Complaint
   ▼
ComplaintIQ
   │
   ▼
Text Processing
   │
   ├──────────────────────────────┐
   │                              │
   ▼                              ▼
Category Prediction          Priority Prediction
(Random Forest)              (Primary Model)
   │                              │
   ▼                              ▼
Confidence Check             Confidence Check
   │                              │
   ├── High → Use Prediction      ├── High → Use Prediction
   │                              │
   └── Low                       └── Low
        │                              │
        ▼                              ▼
   PII Masking                    PII Masking
        │                              │
        ▼                              ▼
      Gemini                         Gemini
        │                              │
        └──────────────┬───────────────┘
                       │
                       ▼
             Final Predictions
                       │
                       ▼
             Store Complaint
             + Predictions
                       │
                       ▼
               Admin Dashboard
                       │
              ┌────────┴────────┐
              │                 │
              ▼                 ▼
        Review Complaint   Review Prediction
              │                 │
              └────────┬────────┘
                       ▼
                 Submit Response
                       │
                       ▼
                    Resolved
                       │
                       ▼
              Customer Dashboard
                       │
                       ▼
                 View Response

```
---

## AI Prediction Flow

ComplaintIQ uses a model-first approach — it does not send every complaint to Gemini.

### Category

```text
Complaint
    ↓
Random Forest
    ↓
Confidence Check
    ├── Sufficient Confidence
    │        ↓
    │   Use Random Forest Prediction
    │
    └── Low Confidence
             ↓
        Mask PII from Complaint
             ↓
           Gemini
             ↓
      Final Category
```

### Priority

```text
Complaint
    ↓
Primary prediction
    ↓
Confidence Check
    ├── Sufficient confidence → Use primary prediction
    └── Low confidence       → Gemini fallback
```

This reduces unnecessary Gemini calls while providing a fallback for uncertain cases.

The system also stores the prediction source separately rather than assuming every prediction came from the same model:

```text
Category predicted by:  Random Forest
Priority predicted by:  Gemini
```

This makes the AI decision process transparent to administrators.

---

## Privacy and PII Protection

Before complaint text is sent to Gemini, ComplaintIQ applies a PII-masking layer.

Examples of information that may be masked:

- Email addresses
- Phone numbers
- Aadhaar/PAN-like identifiers
- Banking-related information
- Other detectable personal information

The masking layer is a privacy safeguard and is not intended to guarantee complete detection of every possible form of PII. Original complaint information remains available within the application.

---

## Technology Stack

| Layer                  | Technology                     |
| ---------------------- | ------------------------------ |
| Backend                | Python, Flask                  |
| Database               | SQLite                         |
| Machine Learning       | Scikit-learn                   |
| Classification Model   | Random Forest                  |
| Generative AI          | Google Gemini API              |
| Data Processing        | Pandas, NumPy                  |
| Frontend               | HTML, CSS, JavaScript          |
| Styling                | Custom CSS                     |
| Theme System           | CSS Variables + localStorage   |
| Environment Management | `.env` / Environment Variables |


---

## Project Structure


```text
ComplaintIQ/
│
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── gemini_service.py
│   ├── predictor.py
│   ├── semantic_similarity.py
│   │
│   ├── static/
│   │   ├── css/
│   │   │   ├── auth.css
│   │   │   └── dashboard.css
│   │   │
│   │   └── js/
│   │       ├── auth.js
│   │       └── dashboard.js
│   │
│   └── templates/
│       ├── admin/
│       │   ├── complaint_detail.html
│       │   └── dashboard.html
│       │
│       ├── auth/
│       │   ├── login.html
│       │   └── signup.html
│       │
│       └── customer/
│           └── dashboard.html
│
├── datasets/
│   └── complaintiq_cleaned_dataset.csv
│
├── trained_models/
│   ├── category_model.pkl
│   ├── priority_model.pkl
│   └── tfidf_vectorizer.pkl
│
├── tests/
│   └── test_priority_fallback.py
│
├── app.py
├── README.md
├── requirements.txt
├── .gitignore
└── .gitattributes

```

---

## Getting Started

### Prerequisites

- Python 3.10+
- pip
- Git
- A Google Gemini API key

### Installation

Clone the repository:

```bash
git clone https://github.com/Aqifcodes/ComplaintIQ.git
cd ComplaintIQ
```

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

### Environment Variables

ComplaintIQ uses environment variables to securely store the Gemini API credentials.

Set the following variables in your system environment:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### Running the Application

```powershell
python app.py
```

Then open the URL shown in the terminal, for example:

```
http://127.0.0.1:5000
```

---

## Application Workflow

### Customer

```text
Login → Submit Complaint → AI Analysis → View Status → View Admin Response
```


### Administrator

```text
Login → View Complaints → Filter → Open Complaint → Review AI Analysis → Submit Response → Resolved
```

### Customer (Post-Response)

```text
Status: Resolved

Admin Response:
<administrator response>
```

---

## Prediction Transparency

Administrators can inspect the full prediction breakdown for each complaint:

```text
Category:              IT Support
Category Confidence:   82.4%
Predicted by:          Random Forest

Priority:              High
Priority Confidence:   78.1%
Predicted by:          Gemini
```

This distinguishes predictions from the trained ML model versus those produced through the Gemini fallback.

---

## Database

ComplaintIQ uses SQLite for local persistence. The database stores:

- User information
- Complaint title and description
- Predicted category and priority
- Category and priority confidence scores
- Category and priority prediction sources
- Complaint status
- Administrator response
- Creation timestamp

---

## UI and UX

ComplaintIQ uses a custom dashboard interface built around a simple complaint management workflow.

The interface includes:

- Light mode and dark mode
- Theme switching with persistent preference via `localStorage`
- Customer dashboard and admin dashboard
- Complaint detail pages
- Complaint status badges
- Category and priority filters
- Clear AI prediction information display
- Direct customer–admin communication

---

## Security Considerations

ComplaintIQ is currently a learning and portfolio project. The application includes basic security measures such as password hashing, environment-based API key management, and role-based access control.

For a production deployment, additional security hardening would be required, including:

- CSRF protection
- Production-grade database
- HTTPS/TLS
- Audit logging
- Further role-based authorization hardening

---

## Limitations

- ML performance depends on the quality and coverage of the training data.
- Gemini fallback requires a valid API key. PII masking cannot guarantee detection of every sensitive value.
- AI predictions are decision-support outputs and should be reviewed by administrators before action.

---

## Future Improvements

- Complaint analytics dashboard
- Email notifications
- Production database support
- Duplicate complaint detection

---
## License

This project is licensed under the MIT License.

See the `LICENSE` file for details.

---

## Author

**Aqif**  
B.Tech CSE (AI & ML)  
GitHub: [Aqifcodes](https://github.com/Aqifcodes)

---

## Acknowledgements

- [Scikit-learn](https://scikit-learn.org/) - machine learning utilities
- [Google Gemini](https://ai.google.dev/) - generative AI capabilities
- [Flask](https://flask.palletsprojects.com/) - web application framework
- Python ecosystem - supporting data and web development libraries

---

## Disclaimer

ComplaintIQ is an AI-assisted complaint management system. AI-generated classifications and recommendations may be incorrect. Administrators should review each complaint and the supporting information before taking action. The system is intended to assist complaint management, not replace human judgment.