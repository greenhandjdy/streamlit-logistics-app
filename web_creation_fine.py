import streamlit as st
import sqlite3
from twilio.rest import Client
import time

# Initialize database connection and ensure the 'log' column exists
def init_db():
    conn = sqlite3.connect('items.db')
    c = conn.cursor()
    # Create table if not exists
    c.execute('''CREATE TABLE IF NOT EXISTS items
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, item TEXT, phone TEXT, status TEXT, arrival_time TEXT)''')
    
    # Add the 'log' column if it doesn't exist
    try:
        c.execute("ALTER TABLE items ADD COLUMN log TEXT")
    except sqlite3.OperationalError:
        # Ignore if the column already exists
        pass
    conn.commit()
    return conn, c

# Function to send SMS via Twilio
def send_sms(phone, message):
    account_sid = 'your_twilio_account_sid'
    auth_token = 'your_twilio_auth_token'
    try:
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            to=phone,
            from_='your_twilio_phone_number',
            body=message
        )
        return message.sid
    except Exception as e:
        return f"SMS sending failed: {str(e)}"

# Function to add item
def add_item(c, name, item, phone):
    arrival_time = time.strftime('%Y-%m-%d %H:%M:%S')
    log = f"Item created at {arrival_time}\n"
    c.execute("INSERT INTO items (name, item, phone, status, arrival_time, log) VALUES (?, ?, ?, ?, ?, ?)", 
              (name, item, phone, 'pending', arrival_time, log))
    
# Function to update item status and log
def update_status(c, item_id, new_status, additional_log=""):
    current_time = time.strftime('%Y-%m-%d %H:%M:%S')
    log_update = f"Status updated to {new_status} at {current_time}\n{additional_log}"
    c.execute("UPDATE items SET status=?, log=log || ? WHERE id=?", (new_status, log_update, item_id))

# Function to get item by name
def get_item(c, name):
    c.execute("SELECT * FROM items WHERE name=?", (name,))
    return c.fetchall()

# Streamlit UI
st.title('物流管理系统')

# Initialize the database connection
conn, c = init_db()

# Tab layout for item creation and status checking
tab1, tab2 = st.tabs(["创建物品信息", "查询物品状态"])

with tab1:
    st.header("添加物品信息")
    
    # Input fields with validation
    name = st.text_input("姓名")
    item = st.text_input("物品名称")
    phone = st.text_input("手机号码", max_chars=11)
    
    if st.button("提交"):
        if name and item and phone:
            if phone.isdigit() and len(phone) == 11:  # Basic phone validation
                add_item(c, name, item, phone)
                conn.commit()
                st.success(f"已添加物品信息！姓名: {name}, 物品: {item}")
            else:
                st.error("请输入有效的手机号码（11位数字）")
        else:
            st.error("请填写所有字段")

with tab2:
    st.header("查询物品状态")
    search_name = st.text_input("输入姓名查询物品")
    
    if st.button("查询"):
        results = get_item(c, search_name)
        if results:
            for idx, row in enumerate(results):
                item_id = row[0]
                st.write(f"物品ID: {item_id}, 姓名: {row[1]}, 物品: {row[2]}, 状态: {row[4]}, 到达时间: {row[5]}")
                
                # 给 text_area 一个唯一的 key，使用 item_id 或 idx
                st.text_area("操作日志", row[6], height=100, key=f"log_{item_id}")
                
                # Dropdown to update status
                new_status = st.selectbox("更新状态", ["待处理", "已通知", "已交付"], key=f"status_{item_id}")
                
                if st.button("更新状态", key=f"update_{item_id}"):
                    update_status(c, item_id, new_status)
                    conn.commit()
                    st.success(f"状态已更新为 {new_status}")
                    
                    # Send notification if status is 'notified'
                    if new_status == "notified":
                        sms_result = send_sms(row[3], f"你的物品'{row[2]}'已到达指定地点")
                        st.write(sms_result)
        else:
            st.error("没有找到相关物品信息！")


# Close the database connection
conn.close()
