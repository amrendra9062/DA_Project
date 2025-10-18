# KGP Connect (DA_Project)

A private social network for students featuring user registration and real-time one-on-one chat.

---
## ## How to Run

1.  Install the required libraries:
    ```bash
    pip install -r requirements.txt
    ```

2.  Run the server:
    ```bash
    uvicorn main:app --reload
    ```

3.  Open your browser and go to `http://127.0.0.1:8000`.

---
## ## Testing the Chat Feature

To test the chat, you must simulate two users:
1.  Register and log in as **User A** in a normal browser window.
2.  Register and log in as **User B** in an **Incognito/Private** window.
3.  Navigate to "Find Users" and start a conversation.