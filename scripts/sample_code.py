import os
import sqlite3

# Hardcoded secret (Security agent should catch this)
API_KEY = "sk-prod-supersecretkey123"

def get_user(user_id):
    conn = sqlite3.connect("users.db")
    # SQL injection vulnerability (Security agent should catch this)
    query = f"SELECT * FROM users WHERE id = {user_id}"
    result = conn.execute(query)
    return result

def process_users(users):
    # N+1 problem (Performance agent should catch this)
    for user in users:
        for item in users:      # Nested loop — O(n²)
            print(user, item)

def x(a, b, c, d, e):          # Bad naming (Quality agent should catch this)
    return a+b+c+d+e