create database flask_auth;

use flask_auth;

create table users(
id INT primary key AUTO_INCREMENT,
    username VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(100) NOT NULL);

create table notes(
note_id int primary key unique not null auto_increment,
	username VARCHAR(100) not null,
	note varchar(100) );






DROP DATABASE IF EXISTS movie_recs;
CREATE DATABASE movie_recs CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE movie_recs;

CREATE TABLE movies (
    id INT AUTO_INCREMENT PRIMARY KEY,   -- we reuse TMDB's id here
    title VARCHAR(200) NOT NULL,
    year INT,
    genres VARCHAR(255),                 -- 'Action|Sci-Fi'
    actors VARCHAR(500),                 -- top 5 billed actors
    director VARCHAR(200),
    plot TEXT,
    keywords TEXT,                       -- 'dream|heist|subconscious'
    popularity FLOAT DEFAULT 0
);

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    preference VARCHAR(20) NOT NULL DEFAULT 'balanced'
);

CREATE TABLE watch_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    movie_id INT NOT NULL,
    rating TINYINT NULL,                 -- 1 to 5, or NULL = not rated
    watched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY one_entry_per_movie (user_id, movie_id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (movie_id) REFERENCES movies(id)
);

CREATE TABLE search_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    query VARCHAR(200),
    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
