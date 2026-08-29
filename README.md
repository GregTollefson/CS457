# CS457 – Database Management Systems

Coursework, assignments, examples, and supporting code for **CS457 – Database Management Systems**.

## Repository Overview

This repository contains programming assignments and related work completed as part of CS457. The repository will be expanded throughout the semester as additional database concepts, technologies, and assignments are introduced.

## Repository Structure

```text id="czd79u"
CS457/
├── 1assignment/
│   ├── README.md
│   ├── makeFinalSchedule.py
│   ├── courses.csv
│   └── ...
│
└── README.md
```

Each assignment directory contains its own README with additional information about the problem, implementation, dependencies, and execution instructions.

## Assignments

### Assignment 1 – UNR Final Exam Schedule Scraper

A Python application that retrieves the University of Nevada, Reno final exam schedule from the web and matches it against a student's course schedule.

The project uses:

* Python
* Requests
* Beautiful Soup
* Pandas
* CSV file I/O
* DataFrames
* Data cleaning and normalization
* Composite-key matching
* Relational-style joins

The assignment provides an introductory data-processing pipeline:

```text id="1ex0lm"
Web Page
   |
   v
HTTP Request
   |
   v
HTML
   |
   v
Beautiful Soup
   |
   v
Structured Data
   |
   v
Pandas DataFrame
   |
   +---------- Course Schedule CSV
   |                    |
   |                    v
   +-------------- DataFrame
                 |
                 v
             Merge / Join
                 |
                 v
        Final Exam Schedule
```

See the `1assignment/README.md` file for implementation details.

## Development Environment

Development is primarily performed using:

* Windows 11
* Windows Subsystem for Linux (WSL / Ubuntu)
* Visual Studio Code
* Python virtual environments
* Jupyter Notebook for exploratory work
* Git and GitHub for version control

Individual assignments may use additional database systems, programming languages, libraries, or development tools as required by the course.

## Python Environment

Python assignments use project-specific virtual environments where appropriate.

A typical environment can be created with:

```bash id="p3n55b"
python3 -m venv .venv
source .venv/bin/activate
```

Dependencies are then installed within the virtual environment rather than globally.

For example:

```bash id="bs2tio"
pip install requests beautifulsoup4 pandas
```

Assignment-specific dependencies and setup instructions are documented within each assignment directory.

## Topics

Topics and examples will be added as they are covered during the course. Areas of study may include:

* Relational database concepts
* Data modeling
* SQL
* Relational algebra
* Database design
* Keys and relationships
* Joins
* Data normalization
* Query processing
* Transactions
* Database programming
* Data acquisition and transformation

## Repository Organization

The repository is organized by assignment or topic rather than as a single software application. Code in one directory should generally be treated independently from code in another unless otherwise noted.

```text id="8q2x34"
CS457
 |
 +-- Assignment 1
 |
 +-- Assignment 2
 |
 +-- Assignment 3
 |
 +-- ...
```

Additional directories will be added as the semester progresses.

## Purpose

The primary purpose of this repository is to document coursework and provide a record of implementations, experiments, and database-related programming exercises completed during CS457.

Where appropriate, assignments include documentation explaining both the implementation and the database/data-management concepts demonstrated by the project.
