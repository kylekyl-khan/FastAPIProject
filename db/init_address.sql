CREATE DATABASE address;
GO
USE address;
GO
CREATE TABLE addresslist (
    name NVARCHAR(255) NOT NULL,
    parent NVARCHAR(255) NULL,
    mail NVARCHAR(255) NOT NULL
);
INSERT INTO addresslist (name, parent, mail) VALUES
('Company', NULL, 'info@example.com'),
('Management', 'Company', 'management@example.com'),
('Engineering', 'Company', 'engineering@example.com'),
('Alice Chen', 'Engineering', 'alice.chen@example.com'),
('Bob Wu', 'Engineering', 'bob.wu@example.com');
