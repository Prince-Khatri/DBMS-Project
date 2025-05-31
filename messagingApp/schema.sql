-- Drop existing tables if they exist
DROP TABLE IF EXISTS user_group;
DROP TABLE IF EXISTS Message;
DROP TABLE IF EXISTS group_table;
DROP TABLE IF EXISTS User;

-- Create User table with enhanced fields
CREATE TABLE User (
    User_Id INT PRIMARY KEY AUTO_INCREMENT,
    Name VARCHAR(100) NOT NULL,
    Email VARCHAR(100) NOT NULL UNIQUE,
    Password VARCHAR(100) NOT NULL,
    Profile_Picture VARCHAR(255),
    Status ENUM('online', 'offline') DEFAULT 'offline',
    Last_Seen DATETIME,
    Phone_Number VARCHAR(20),
    Bio TEXT,
    Created_At DATETIME DEFAULT CURRENT_TIMESTAMP,
    Updated_At DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Create group_table with enhanced fields
CREATE TABLE group_table (
    group_id INT PRIMARY KEY AUTO_INCREMENT,
    group_name VARCHAR(100) NOT NULL,
    group_description TEXT,
    group_picture VARCHAR(255),
    group_type ENUM('public', 'private') DEFAULT 'private',
    created_on DATETIME DEFAULT CURRENT_TIMESTAMP,
    admin_email VARCHAR(100),
    last_activity DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_email) REFERENCES User(Email)
);

-- Create Message table with enhanced fields
CREATE TABLE Message (
    message_id INT PRIMARY KEY AUTO_INCREMENT,
    sender_user_id INT,
    receiver_user_id INT,
    receiver_group_id INT,
    content TEXT,
    message_type ENUM('text', 'image', 'file', 'audio', 'video') DEFAULT 'text',
    message_status ENUM('sent', 'delivered', 'read') DEFAULT 'sent',
    reply_to_message_id INT,
    file_url VARCHAR(255),
    sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender_user_id) REFERENCES User(User_Id),
    FOREIGN KEY (receiver_user_id) REFERENCES User(User_Id),
    FOREIGN KEY (receiver_group_id) REFERENCES group_table(group_id),
    FOREIGN KEY (reply_to_message_id) REFERENCES Message(message_id)
);

-- Create user_group table with enhanced fields
CREATE TABLE user_group (
    user_id INT,
    group_id INT,
    role ENUM('admin', 'member') DEFAULT 'member',
    joined_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    notification_settings JSON,
    PRIMARY KEY (user_id, group_id),
    FOREIGN KEY (user_id) REFERENCES User(User_Id),
    FOREIGN KEY (group_id) REFERENCES group_table(group_id)
);

-- Create indexes for better performance
CREATE INDEX idx_user_email ON User(Email);
CREATE INDEX idx_message_sender ON Message(sender_user_id);
CREATE INDEX idx_message_receiver ON Message(receiver_user_id);
CREATE INDEX idx_message_group ON Message(receiver_group_id);
CREATE INDEX idx_group_admin ON group_table(admin_email);
CREATE INDEX idx_user_group_user ON user_group(user_id);
 