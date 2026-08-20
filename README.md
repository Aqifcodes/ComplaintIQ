## ComplaintIQ

AI-Powered Complaint Intelligence Platform

ComplaintIQ is a web-based complaint management platform that helps organizations classify, prioritize, and manage customer complaints using Machine Learning and Gemini AI.

The platform connects two sides of the complaint process:


Customer → Complaint Submission → AI Analysis → Management → Admin Response → Customer

### Features

#### Customer

- User registration and login
- Submit complaints with title and description
- Automatic complaint category prediction
- Automatic priority prediction
- AI fallback for low-confidence predictions
- View submitted complaints
- Track complaint status
- View management/admin responses
- Light and dark mode
- PII masking before sending complaint text to external AI services

#### Admin / Management

- Separate admin login
- View all submitted complaints
- Filter complaints by category and priority
- View complaint details
- View predicted category and priority
- View prediction confidence
- See which system produced the prediction
- Respond to complaints
- Mark complaints as resolved
- Customer sees the response and resolved status

### AI / ML Workflow

ComplaintIQ uses a hybrid prediction approach.

#### Category Prediction

The primary category classifier uses a trained Random Forest model with TF-IDF text features.

If the Random Forest confidence is high enough, its prediction is used directly.

If the confidence is below the configured threshold, Gemini is used as a fallback semantic classifier.

For categories that do not fit the existing category set, the system can use semantic similarity to determine whether the proposed category is similar to an existing pending category or should be treated as a new category.

#### Priority Prediction

Priority is predicted using the configured ML/Gemini workflow.

When the primary model is not sufficiently confident, Gemini can be used as the fallback.

The system keeps the prediction source visible to administrators so they can understand how the prediction was produced.

### Semantic Similarity

ComplaintIQ uses the `all-MiniLM-L6-v2` Sentence Transformer model for semantic similarity.

Instead of comparing categories only by exact words, the system converts category names into vector embeddings and compares their cosine similarity.

For example:

`Facilities Management`

and

`Workplace Facilities`

can be recognized as semantically related even though the wording is different.

The current similarity threshold is configured in the application rather than being hardcoded into the UI.

### Technology Stack

#### Backend

- Python
- Flask
- SQLite
- Werkzeug Authentication

#### Machine Learning

- Scikit-learn
- TF-IDF
- Random Forest
- Sentence Transformers
- Cosine Similarity

#### AI

- Google Gemini API

#### Frontend

- HTML
- CSS
- JavaScript
- Jinja2
- Font Awesome

### Future Improvements

Possible future improvements include:

More advanced complaint analytics
Email notifications
Complaint resolution feedback
Production database and deployment

### Project Goal

ComplaintIQ aims to reduce the manual effort involved in handling large numbers of complaints by automatically organizing incoming complaints, identifying their priority, and connecting them with the appropriate management workflow.

The goal is not to replace management decisions, but to help management process complaints faster and more consistently.

Built as a AI & ML project.