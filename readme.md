# Canteen Connect: A Modern Solution for Campus Eateries

**Canteen Connect** is a full-stack web application developed as a submission for the "Builder's Day" challenge, the second round of the campus placement process for **KeyValue Software Systems**. This project was built from concept to cloud deployment in a rapid, iterative fashion, showcasing modern development practices and the strategic use of AI-powered tools to accelerate the build-test-deploy lifecycle.

**Live Demo:** [https://canteen-service-1055948577637.asia-south1.run.app](https://canteen-service-1055948577637.asia-south1.run.app)

---

## The Problem: The Daily Canteen Chaos

St. Xavier's Engineering College canteen, managed by Chandrettan, faced a daily operational crisis:
* **Long Queues:** Students wasted up to 45 minutes in queues, impacting their study time.
* **Demand Uncertainty:** With no pre-ordering, Chandrettan had to guess the number of meals to prepare, leading to either significant food wastage (40+ plates daily) or running out of food early.
* **Payment Nightmares:** An informal credit system resulted in over ₹15,000 in pending dues, tracked inefficiently in a physical notebook.
* **Student Dissatisfaction:** When meals ran out, students were forced to spend more money at outside vendors.

The challenge was to build a simple, effective digital solution to bring order to this chaos.

## The Solution: A Centralized Ordering Platform

Canteen Connect is a web portal that digitizes the entire ordering process, creating a seamless experience for both students and the canteen manager.

* **For Students:** A simple, intuitive interface to view the menu, pre-order meals, and see their order history.
* **For Admins (Chandrettan):** A secure dashboard to view real-time aggregated demand, manage the daily menu, and track all orders in one place, eliminating guesswork and financial discrepancies.

![KeyValue Builder's Day](https://googleusercontent.com/file_content/0)

---

## My Development Philosophy: AI-Augmented Rapid Prototyping

This project was completed by strategically leveraging modern AI development tools. The key was not to let the AI build the project, but to **command it as a force multiplier**. I was in control of the architecture, the logic, and the end-to-end vision. The AI served as an ultra-efficient junior developer, handling boilerplate code, generating templates, and accelerating debugging cycles.

This approach allowed me to:
* **Focus on High-Level Strategy:** Instead of getting bogged down in syntax, I focused on database schema design, application flow, and the user experience.
* **Accelerate Development:** Repetitive tasks like creating HTML templates, writing database queries, and setting up Flask routes were delegated, reducing development time significantly.
* **Debug with Precision:** When deployment errors occurred, I used the AI to analyze logs and suggest targeted fixes, turning a potentially hours-long debugging session into a rapid, iterative process.

In today's world, knowing how to effectively direct AI tools is a critical skill. This project is a testament to that philosophy—delivering a robust, deployed application at a speed unachievable with traditional methods alone.

---

## Technology Stack

| Area          | Technology                                                              |
|---------------|-------------------------------------------------------------------------|
| **Backend** | Python, Flask                                                           |
| **Frontend** | HTML5, CSS3, Jinja2 Templating                                          |
| **Database** | SQLite                                                                  |
| **Server** | Gunicorn                                                                |
| **Deployment**| Docker, Google Cloud Run, Google Cloud Build, Google Artifact Registry  |

---

## Iterative Development & Deployment

The project was built using an incremental model, with a deployable (though not yet deployed) product after each cycle. This agile approach ensured a solid foundation and allowed for continuous progress.

* **Cycle 1: Foundation & Setup:** Initialized the Flask application structure and established the base project files.
* **Cycle 2: Database Schema Design:** Designed and implemented the database schema (`schema.sql`) for users, admins, menu items, and orders.
* **Cycle 3: User Authentication:** Built the core functionality for student registration and login, including secure password hashing with Werkzeug.
* **Cycle 4: Core Student Features:** Implemented the main student-facing features: viewing the menu, placing an order, and viewing order history.
* **Cycle 5: Admin Panel Foundation:** Created the secure admin login and a basic dashboard structure.
* **Cycle 6: Full Admin CRUD Functionality:** Implemented complete Create, Read, Update, and Delete (CRUD) functionality for menu items.
* **Cycle 7: Containerization:** Wrote the `Dockerfile` to containerize the application, making it portable and ready for cloud deployment.
* **Cycle 8 & 9: Cloud Deployment & Debugging:** Deployed the container to Google Cloud Run. This involved multiple sub-cycles of identifying and fixing startup errors related to database initialization and environment-specific issues, hardening the application for a production environment.

---

## Key Features Implemented

### Student-Facing Features
* **Secure Authentication:** Students can register and log in with unique Student IDs. Passwords are securely hashed and never stored in plaintext.
* **Dynamic Menu:** Displays a real-time list of available menu items, pulling directly from the database.
* **Order Placement:** Students can specify a quantity and place an order, which atomically updates the available stock for that item.
* **Order History:** A dedicated page for students to view a history of all their past orders.

### Admin Panel Features
* **Secure Admin Login:** A separate, secure login portal for the canteen manager.
* **Aggregated Demand Dashboard:** The main dashboard shows a real-time, aggregated view of how many of each item have been ordered for the day, solving the core problem of demand prediction.
* **Individual Order Tracking:** A detailed list of every single order placed for the day.
* **Full Menu Management (CRUD):**
    * **Create:** Add new items to the menu.
    * **Read:** View all current menu items and their properties.
    * **Update:** Edit the name, price, and quantity of existing items.
    * **Delete:** Remove items from the menu.
    * **Toggle Availability:** Instantly mark items as "Available" or "Unavailable."

---

## How to Run Locally

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/your-username/canteen-connect.git](https://github.com/your-username/canteen-connect.git)
    cd canteen-connect
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the application:**
    ```bash
    flask run
    ```

5.  Open your browser and navigate to `http://127.0.0.1:5000`.
