import requests
from bs4 import BeautifulSoup
import pandas as pd

def scrape_final_schedule(url):
    # Download the HTML
    response = requests.get(url)

    # Make sure the request succeeded
    response.raise_for_status()

    # Parse the HTML into a Beautiful Soup object
    soup = BeautifulSoup(response.text, "html.parser")

    # Find the table containing the final schedule
    tables = soup.find_all("table")

    # Extract data from the table
    data = []
    for table in tables:
        finals_day = table.caption.get_text(" ", strip=True)

        for row in table.tbody.find_all("tr"):
            class_time = row.find("th", scope="row").get_text(" ", strip=True)

            cells = row.find_all("td")

            class_days = cells[0].get_text(" ", strip=True)
            final_meeting = cells[1].get_text(" ", strip=True)

            data.append({
                "Class Day(s)": class_days,
                "Class time": class_time,
                "Finals Day": finals_day,
                "Final Meeting time": final_meeting
            })

    # Create a DataFrame from the extracted data
    df = pd.DataFrame(data)

    # Split Class Day(s) into separate rows if there are multiple days
    df["Class Day(s)"] = df["Class Day(s)"].str.split(" or ")
    df = df.explode("Class Day(s)", ignore_index=True)

    return df

def load_courses(filename):
    # Load the courses from a CSV file
    courses = pd.read_csv(filename)
    return courses

def merge_schedules(courses_df, finals_df):
    # Merge the courses DataFrame with the finals schedule DataFrame
    merged_df = pd.merge(
        courses_df, finals_df, 
        how="left", 
        left_on=["Day", "Time"], 
        right_on=["Class Day(s)", "Class time"]
    )

    return merged_df.drop(columns=["Class Day(s)", "Class time"])

def main():
    # URL of the final schedule page
    url = "https://www.unr.edu/admissions/records/academic-calendar/finals-schedule"

    # Scrape the final schedule
    finals_df = scrape_final_schedule(url)

    # Load the courses from a CSV file
    courses_df = load_courses("courses.csv")

    # Merge the schedules
    merged_df = merge_schedules(courses_df, finals_df)

    # Save the merged schedule to a new CSV file
    merged_df.to_csv("final_schedule.csv", index=False)

if __name__ == "__main__":
    main()  