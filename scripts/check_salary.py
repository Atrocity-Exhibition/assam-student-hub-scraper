import urllib.request
import json

url = "https://qktomyipkzgdlexhkuqr.supabase.co/rest/v1/"
# We can't query information_schema via standard PostgREST unless exposed,
# but we can try to query a dummy row or check if we get an error on specific columns.
# Let's try select=id,salary on notices and select=id,salary on jobs.
headers = {
    "apikey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFrdG9teWlwa3pnZGxleGhrdXFyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzkxNzUwMjQsImV4cCI6MjA5NDc1MTAyNH0.tqINFXcp52nPIqSCDYs-PfCEIYrv4VqbJf2-JTBlCMI",
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFrdG9teWlwa3pnZGxleGhrdXFyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzkxNzUwMjQsImV4cCI6MjA5NDc1MTAyNH0.tqINFXcp52nPIqSCDYs-PfCEIYrv4VqbJf2-JTBlCMI"
}

def check_col(table, col):
    req = urllib.request.Request(f"{url}{table}?select={col}&limit=1", headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            print(f"Table {table} has column '{col}'!")
            return True
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        print(f"Table {table} checking for '{col}' returned HTTPError {e.code}: {body}")
        return False
    except Exception as e:
        print(f"Error checking {table}.{col}: {e}")
        return False

check_col("notices", "salary")
check_col("notices", "pay_scale")
check_col("jobs", "salary")
check_col("jobs", "pay_scale")
