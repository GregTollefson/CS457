# UNR Final Exam Schedule Scraper

A Python web-scraping project that retrieves the University of Nevada, Reno final exam schedule, converts the schedule into structured data, and matches a student's course schedule with the corresponding final exam days and times.

This project was developed for **CS457 – Database Management Systems**.

## Overview

The program performs the following steps:

1. Downloads the UNR final exam schedule webpage.
2. Parses the HTML using Beautiful Soup.
3. Extracts the final exam scheduling rules from the HTML tables.
4. Converts the extracted data into a Pandas DataFrame.
5. Reads a student's course schedule from a CSV file.
6. Matches each course against the final exam schedule using the class meeting days and class time.
7. Produces a schedule containing the final exam day and meeting time for each course.

The project demonstrates a simple **Extract, Transform, and Match** data-processing pipeline.

```text
UNR Final Exam Schedule
        |
        v
     Requests
        |
        v
   Raw HTML
        |
        v
 Beautiful Soup
        |
        v
Finals DataFrame
        |
        |                courses.csv
        |                     |
        |                     v
        |              Courses DataFrame
        |                     |
        +----------+----------+
                   |
                   v
              Pandas Merge
                   |
                   v
          Final Exam Schedule
```

## Technologies

* Python 3
* Requests
* Beautiful Soup 4
* Pandas

Development and testing were performed using VS Code and Jupyter Notebook in a Python virtual environment.

## Input

The program reads a course schedule from `courses.csv`.

The CSV file has three columns:

```csv
Course,Day,Time
CS457,Monday/Wednesday (MW),7 p.m.
Stat654,Tuesday/Thursday (TR),10:30 a.m.
Math311,Monday/Wednesday/Friday (MWF),9 a.m.
Math466,Monday/Wednesday/Friday (MWF),12 p.m.
```

The `Day` and `Time` values must correspond to the class-day and class-time formats used by the UNR final exam schedule.

## Web Scraping

The final exam schedule is retrieved from the University of Nevada, Reno final exam schedule webpage.

The page contains multiple HTML tables, with each table representing a day of final exams.

Beautiful Soup extracts:

* Finals day from the table `<caption>`
* Class time from the row header `<th>`
* Class meeting days from the first `<td>`
* Final meeting time from the second `<td>`

Some schedule entries contain multiple class-day patterns, such as:

```text
Tuesday/Thursday (TR) or Thursday (R)
```

These values are split and expanded into separate DataFrame rows so that each class-day/time combination can be matched independently.

## Matching the Schedules

The course schedule and final exam schedule are matched using two fields:

```text
Day + Time
```

These correspond to:

```text
courses.Day  <->  finals["Class Day(s)"]
courses.Time <->  finals["Class time"]
```

Pandas performs a left merge on these fields.

Conceptually, this is equivalent to a relational database join using a composite key:

```sql
SELECT *
FROM courses
LEFT JOIN finals
    ON courses.Day = finals.ClassDays
   AND courses.Time = finals.ClassTime;
```

A left join preserves every course in the input schedule. If no corresponding final exam rule is found, the final exam fields remain empty rather than silently removing the course.

## Program Structure

The standalone Python program is organized around a `main()` function and supporting functions.

```text
main()
 |
 +-- scrape_final_schedule()
 |      |
 |      +-- Download webpage
 |      +-- Parse HTML
 |      +-- Extract schedule
 |      +-- Return finals DataFrame
 |      +-- Split multi-day fields in DataFrame
 |
 +-- load_courses()
 |      |
 |      +-- Read input file: courses.csv
 |      +-- Return courses DataFrame
 |
 +-- merge_schedules()
        |
        +-- Match Day and Time using pd.merge
        +-- Return completed schedule
```

The program uses the standard Python entry-point pattern:

```python
if __name__ == "__main__":
    main()
```

## Setup and Running the Program

After extracting the submitted ZIP file, open a terminal in the assignment directory containing `makeFinalSchedule.py`.

The directory should contain:

```text
WorkingDirectory/
├── makeFinalSchedule.py
├── courses.csv
├── requirements.txt
└── README.md
```

### 1. Create a Python virtual environment

```bash
python3 -m venv .venv
```

### 2. Activate the virtual environment

Linux, macOS, or WSL:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Install the required packages

```bash
python -m pip install -r requirements.txt
```

### 4. Run the program

```bash
python makeFinalSchedule.py
```

The program reads the course schedule from `courses.csv`, retrieves the UNR final exam schedule, and matches each course with its corresponding final exam day and time.

### 5. Deactivate the virtual environment

When finished:

```bash
deactivate
```

Output File:  
```
final_schedule.csv
```

Note: The input file `courses.csv` is hardcoded in `makeFinalSchedule.py`

## Development Workflow

A Jupyter Notebook was used initially to explore the HTML structure and prototype the scraping and Pandas operations interactively.

The development process was:

```text
Inspect HTML
    |
    v
Identify tables and fields
    |
    v
Test Beautiful Soup selectors
    |
    v
Build Pandas DataFrame
    |
    v
Normalize schedule data
    |
    v
Test DataFrame merge
    |
    v
Refactor into standalone Python functions
```

This separation made it possible to verify each stage of the data pipeline before incorporating it into the final program.


## Data Source

Final exam scheduling information is obtained from the University of Nevada, Reno final exam schedule webpage:

https://www.unr.edu/admissions/records/academic-calendar/finals-schedule

Because the schedule is retrieved from the live webpage, changes to the page's HTML structure may require corresponding changes to the scraper.

