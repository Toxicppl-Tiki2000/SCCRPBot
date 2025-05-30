CREATE DATABASE larn;
USE larn;

CREATE TABLE ausweise (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    vorname VARCHAR(100),
    geburtsdatum DATE,
    geschlecht ENUM('männlich', 'weiblich', 'divers'),
    unterschrift VARCHAR(255),
    SCCRP TINYINT(1),
    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id BIGINT
);

CREATE TABLE ausweis_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    action_type VARCHAR(50),
    user_id BIGINT,
    username VARCHAR(100),
    guild_name VARCHAR(100),
    ausweis_id INT,
    log_level ENUM('INFO', 'WARN', 'ERROR'),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE bot_admins (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(100),
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE discord_roblox_links (
    discord_user_id BIGINT PRIMARY KEY,
    roblox_user_id BIGINT NOT NULL,
    verknuepft_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



ALTER TABLE ausweise ADD COLUMN roblox_user_id BIGINT NULL;
ALTER TABLE discord_roblox_links ADD COLUMN pending_code VARCHAR(10), ADD COLUMN code_expires_at TIMESTAMP;

