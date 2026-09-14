# Easy

1. Social Media PII Extraction


Problem
Social Media PII Extraction.

You are a data engineer on the privacy engineering team at Meta. Raw user contact data cannot flow into the analytics warehouse as-is: phone numbers must be masked and email addresses reduced to just their domain so analysts can study provider distribution without seeing PII.

Write a query against social_media_pii_input (note: all three columns are stored as text) that produces, for every user: email_domain, the part of email after the @ sign; anon_phone, the literal string ****** followed by the last 4 digits of phone (the phones are 10-digit strings, so the first six digits are masked); and user_id cast to an integer.
Return the columns in the order anon_phone, email_domain, user_id, sorted by anon_phone in ascending order.
Output columns: anon_phone, email_domain, user_id


Schema
1 table
Expand all

social_media_pii_input
3 cols
Examples
Example 1

Input:

social_media_pii_input:

user_id	email	phone
1	alice@example.com	5551234567
2	bob@domain.net	5559876543
3	carol@email.org	5551239876
4	dave@site.com	5554567890
5	eve@platform.io	5559871234
Output:

anon_phone	email_domain	user_id
******1234	platform.io	5
******4567	example.com	1
******6543	domain.net	2
******7890	site.com	4
******9876	email.org	3
Explanation: User 5's phone 5559871234 becomes ******1234 and eve@platform.io is reduced to platform.io. Because rows are sorted by the masked phone string, user 5 (...1234) comes first and user 3 (...9876) comes last, so the output is not in user_id order.

Constraints
email_domain is the substring of email after the @ sign
anon_phone is the literal string ****** followed by the last 4 digits of phone (first six digits masked)
user_id must be cast from text to an integer
Column order must be exactly anon_phone, email_domain, user_id
Sort by anon_phone in ascending order (string sort; the output is not in user_id order)

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql import Window as W
import pyspark
import datetime
import json

spark = SparkSession.builder.appName('run-pyspark-code').getOrCreate()

def etl(input_df):
    # Write code here
    pass

2. Social Media Text Correction
Problem
A social-media export contains posts whose text uses an outdated product name. Return every post while replacing each case-sensitive occurrence of Python in text with PySpark; leave all other text unchanged. Preserve the requested output columns and order rows by comments ascending.

Output columns: comments, date, id, likes, platform, shares, text

date identifies the relevant date.


Schema
1 table
Expand all

correct_social_media_post
7 cols
Examples
Example 1

Input:

correct_social_media_post:

id	date	text	likes	shares	comments	platform
1	2022-03-01	This is a Python post.	10	2	3	Twitter
2	2022-03-02	Another post about Python.	20	3	5	Instagram
3	2022-03-03	Python is great for data analysis.	30	4	2	Facebook
4	2022-03-04	I am learning Python for machine learning.	40	5	7	Twitter
5	2022-03-05	Python vs. R for data science.	50	6	9	Instagram
6	2022-03-06	Python web development is awesome.	60	1	1	Facebook
7	2022-03-07	Python for finance.	70	3	4	Twitter
8	2022-03-08	Python libraries for data visualization.	80	2	6	Instagram
Output:

comments	date	id	likes	platform	shares	text
1	2022-03-06	6	60	Facebook	1	PySpark web development is awesome.
2	2022-03-03	3	30	Facebook	4	PySpark is great for data analysis.
3	2022-03-01	1	10	Twitter	2	This is a PySpark post.
4	2022-03-07	7	70	Twitter	3	PySpark for finance.
5	2022-03-02	2	20	Instagram	3	Another post about PySpark.
6	2022-03-08	8	80	Instagram	2	PySpark libraries for data visualization.
7	2022-03-04	4	40	Twitter	5	I am learning PySpark for machine learning.
9	2022-03-05	5	50	Instagram	6	PySpark vs. R for data science.
Explanation: Post 6 changes Python web development is awesome. to PySpark web development is awesome. and appears first because its comments value is 1.

Constraints
Use every supplied input row when calculating the result.
Preserve the calculation, filtering, tie handling, and ordering described in the problem.
Return results matching the expected output schema and order.


from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql import Window as W
import pyspark
import datetime
import json

spark = SparkSession.builder.appName('run-pyspark-code').getOrCreate()

def etl(social_media):
    # Write code here
    pass


3. Call Center Performance Metrics

Problem
Build a daily call-volume summary for the support floor.

You are a data analyst at a telecommunications company. The call-center operations lead wants a per-day summary of how many distinct customers called in and how much total talk time was logged, so staffing can be matched to demand. Note that this raw feed lands with every column stored as text, so numeric values must be cast before aggregating.

For each date, report the number of distinct known customers who called that day (num_customers) and the total call duration logged that day (total_duration), casting duration from text to integer before summing. Only calls from customers listed in cc_customer count. Return both aggregates as integers and sort the results by date in ascending order.

Output columns: date, num_customers, total_duration


Schema
2 tables
Expand all

cc_calls
4 cols

cc_customer
5 cols
Examples
Example 1

Input:

cc_calls:

call_id	cust_id	date	duration
1	1	2022-01-01	100
2	2	2022-01-01	200
3	1	2022-01-02	150
4	3	2022-01-02	300
5	2	2022-01-03	50
6	1	2022-01-04	120
7	1	2022-01-04	80
8	99	2022-01-04	500
cc_customer:

cust_id	name	state	tenure	occupation
1	Alice	NY	10	doctor
2	Bob	CA	12	lawyer
3	Charlie	TX	6	engineer
Output:

date	num_customers	total_duration
2022-01-01	2	300
2022-01-02	2	450
2022-01-03	1	50
2022-01-04	1	200
Explanation: On 2022-01-01, customers 1 and 2 called (2 distinct customers) for 100 + 200 = 300 total duration. On 2022-01-03 only customer 2 called, giving 1 distinct customer and 50 total duration. Days are listed in ascending date order.

Constraints
The raw call feed may contain cust_id values with no matching row in cc_customer; those calls must be excluded from both aggregates. A customer with several calls on the same date counts once in num_customers, while every one of their calls contributes to total_duration.

All columns are stored as text; cast duration to integer before summing

Only calls from customers listed in cc_customer count

num_customers counts distinct customers per day, not total calls

Return num_customers and total_duration as integers

Output columns must be exactly date, num_customers, total_duration

Sort results by date in ascending order


from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql import Window as W
import pyspark
import datetime
import json

spark = SparkSession.builder.appName('run-pyspark-code').getOrCreate()

def etl(calls_df, customers_df):
    # Write code here
    pass


4. Research Paper Citation Analysis

Problem
Adobe maintains a catalog of AI research papers and their authors. For each author whose paper_id exists in the paper catalog, assign a position starting at 1 within that paper, with smaller author_id values appearing first. Return author_id, name, paper_id, and row_number, ordered by paper and then position.

Output columns: author_id, name, paper_id, row_number

row_number is the author's 1-based position within the paper.


Schema
2 tables
Expand all

ai_author
3 cols
paper_id
VARCHAR
author_id
VARCHAR
name
VARCHAR

ai_research_papers
3 cols
paper_id
VARCHAR
title
VARCHAR
year
VARCHAR
Examples
Example 1

Input:

ai_author:

author_id	name	paper_id
A2	Bob	P1
A1	Alice	P1
A3	Carol	P2
A9	Nora	P9
ai_research_papers:

paper_id	title	year
P1	Model Evaluation	2025
P2	Efficient Training	2026
Output:

author_id	name	paper_id	row_number
A1	Alice	P1	1
A2	Bob	P1	2
A3	Carol	P2	1
Explanation: Paper P1 has authors A1 and A2, so A1 receives position 1 and A2 receives position 2; A9 is omitted because P9 is absent from the paper catalog.

Constraints
Use every supplied input row when calculating the result.
Preserve the calculation, filtering, tie handling, and ordering described in the problem.
Return results matching the expected output schema and order.


from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql import Window as W
import pyspark
import datetime
import json

spark = SparkSession.builder.appName('run-pyspark-code').getOrCreate()

def etl(authors, research_papers):
    # Write code here
    pass

5. Insurance Customer Data Merge
Problem
Consolidate two regional customer books into one list.

You are a data engineer at Databricks working with an insurance client. The client's customer records live in two separate tables that came from different regional systems, ic_data_1 and ic_data_2, with identical schemas. They want a single consolidated list for the underwriting team.

Write a query that combines all rows from ic_data_1 and ic_data_2 using a UNION ALL — do not deduplicate; every row from both tables must appear in the result. Return the columns customer_id, first_name, last_name, age, and policy_type, and sort the combined result by age in ascending order.

Output columns: customer_id, first_name, last_name, age, policy_type


Schema
2 tables
Expand all

ic_data_1
5 cols
customer_id
INT
first_name
VARCHAR
last_name
VARCHAR
age
INT
policy_type
VARCHAR

ic_data_2
5 cols
customer_id
INT
first_name
VARCHAR
last_name
VARCHAR
age
INT
policy_type
VARCHAR
Examples
Example 1

Input:

ic_data_1:

customer_id	first_name	last_name	age	policy_type
1	Alice	Smith	30	auto
2	Bob	Johnson	40	home
3	Carol	Williams	35	life
ic_data_2:

customer_id	first_name	last_name	age	policy_type
4	Dave	Brown	45	auto
5	Eve	Jones	55	health
6	Frank	Davis	60	life
Output:

customer_id	first_name	last_name	age	policy_type
1	Alice	Smith	30	auto
3	Carol	Williams	35	life
2	Bob	Johnson	40	home
4	Dave	Brown	45	auto
5	Eve	Jones	55	health
6	Frank	Davis	60	life
Explanation: All 3 rows from each table appear in the combined result of 6 rows. Sorting by age puts Alice (30) first and interleaves the two sources — Carol (35) from ic_data_1 comes before Bob (40), and Dave (45) from ic_data_2 follows.

Constraints
Return exactly the columns customer_id, first_name, last_name, age, policy_type.
Use UNION ALL semantics: keep every row from both tables and do not deduplicate.
Sort the combined result by age ascending.

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql import Window as W
import pyspark
import datetime
import json

spark = SparkSession.builder.appName('run-pyspark-code').getOrCreate()

def etl(ic_data_1, ic_data_2):
    #write your code here

6. Monthly Average Rating Tracker

Problem
You have a mr_reviews table where each row is a star rating a user left for a product on a given date. For every product and every calendar month in which it received ratings, report the product's average star rating. Return the month as its numeric value (mth), the product's ID (product), and the average rating rounded to two decimal places (avg_stars). Sort the results by month, then by product ID.

Output columns: mth, product, avg_stars

Sort the results by mth, product.


Schema
1 table
Expand all

mr_reviews
6 cols
review_id
INT
user_id
INT
submit_date
DATE
product_id
INT
stars
INT
month
INT
Examples
Example 1

Input:

mr_reviews:

review_id	user_id	submit_date	product_id	stars	month
6171	123	2022-06-08	50001	4	6
7802	265	2022-06-10	69852	4	6
5293	362	2022-06-18	50001	3	6
6352	192	2022-07-26	69852	3	7
4517	981	2022-07-05	69852	2	7
Output:

mth	product	avg_stars
6	50001	3.50
6	69852	4.00
7	69852	2.50
Explanation: Product 50001 has two June ratings, 4 and 3, so its June average is (4 + 3) / 2 = 3.50. Product 69852 has two July ratings, 3 and 2, giving a July average of (3 + 2) / 2 = 2.50.

Constraints
The month is taken from submit_date.
avg_stars is rounded to two decimal places.
Return results matching the expected output schema and order.

from pyspark.sql import SparkSession
from pyspark.sql.functions import month, avg, col

def etl(input_df):
    pass


7. Post Frequency Gap Analysis

Problem
A social platform stores every post its users published, with the timestamp of each post. For each user who published at least two posts during the year 2021, report how many days separated that user's earliest 2021 post from their latest 2021 post. Posts outside 2021 are ignored entirely, and a user who posted only once in 2021 should not appear.

Return one row per qualifying user with user_id and days_between, where days_between is the number of calendar days between the dates of that user's first and last 2021 post.

Output columns: user_id, days_between


Schema
1 table
Expand all

post_gap_posts
4 cols
user_id
INT
post_id
INT
post_content
VARCHAR
post_date
TIMESTAMP
Examples
Example 1

Input:

post_gap_posts:

user_id	post_id	post_content	post_date
101	1	First post of 2021	2021-01-01 08:00:00
101	7	Final post of the year	2021-12-31 23:59:00
202	2	Second post of 2021	2021-01-05 09:30:00
303	3	Another post in 2021	2021-01-07 18:00:00
303	6	Enjoying life	2021-01-15 22:00:00
303	8	Happy new year 2022	2022-01-02 10:00:00
Output:

user_id	days_between
101	364
303	8
Explanation: User 101 posted twice in 2021, on 2021-01-01 and 2021-12-31, which are 364 days apart. User 303 has two qualifying 2021 posts on 2021-01-07 and 2021-01-15 (8 days apart); the 2022-01-02 post is outside 2021 and is not counted. User 202 posted only once in 2021, so they are excluded.

Constraints
Only posts with a post_date in the year 2021 are considered.
A user must have at least two 2021 posts to appear in the result.
days_between is the whole number of days between the calendar dates of the first and last qualifying post.
Return results matching the expected output schema and order.


-- Write query here
-- TABLE NAME: `post_gap_posts`


8. Most Active Team Members
Problem
You are given a table of messages exchanged on a messaging platform. Your task is to identify the top 2 users who sent the highest number of messages in August 2022. Objective Write a SQL query to: Count the total number of messages sent by each user in August 2022.

Output columns: sender_id, message_count


Schema
1 table
Expand all

ttu_messages
5 cols
message_id
INT
sender_id
INT
receiver_id
INT
content
VARCHAR
sent_date
TIMESTAMP
Examples
Example 1

Input:

ttu_messages:

message_id	sender_id	receiver_id	content	sent_date
901	3601	4500	You up?	2022-08-03 00:00:00
902	4500	3601	Only if you are buying	2022-08-03 00:00:00
743	3601	8752	Went offline	2022-06-14 00:00:00
922	3601	4500	Get on the call	2022-08-10 00:00:00
Output:

sender_id	message_count
3601	2
4500	1
Constraints
Handle NULL values appropriately
Return results matching the expected output schema and order

-- Write query here
-- TABLE NAME: `ttu_messages`

9. Leading Manufacturer Sales

Problem
CVS Health wants to compare drug sales across pharmaceutical manufacturers. Each row in tms_pharma_in is one drug, with the revenue it generated in total_sales. Report every manufacturer alongside the combined sales of all its drugs, expressed to the nearest million dollars as the text $<n> million. List the manufacturer with the highest combined sales first, breaking ties alphabetically by manufacturer name.

Output columns: manufacturer, sale


Schema
1 table
Expand all

tms_pharma_in
6 cols
product_id
INT
units_sold
INT
total_sales
DECIMAL
cogs
DECIMAL
manufacturer
VARCHAR
drug
VARCHAR
Examples
Example 1

Input:

tms_pharma_in:

product_id	units_sold	total_sales	cogs	manufacturer	drug
94	132362	2041758.41	1373721.7	Biogen	UP and UP
9	37410	293452.54	208876.01	Eli Lilly	Zyprexa
50	90484	2521023.73	2742445.9	Eli Lilly	Dermasorb
61	77023	500101.61	419174.97	Biogen	Varicose Relief
136	144814	1084258	1006447.73	Biogen	Burkhart
Output:

manufacturer	sale
Biogen	$4 million
Eli Lilly	$3 million
Explanation: Biogen's three drugs sum to 2041758.41 + 500101.61 + 1084258 = 3626118.02, which rounds to $4 million. Eli Lilly's two drugs sum to 293452.54 + 2521023.73 = 2814476.27, which rounds to $3 million. Biogen has the larger combined sales, so it is listed first.

Constraints
Combined sales are rounded to the nearest million and formatted as the text $<n> million.
Order by combined sales from highest to lowest, then by manufacturer name alphabetically for ties.
Return results matching the expected output schema and order.

-- Write query here
-- TABLE NAME: `tms_pharma_in`

10. Pharmaceutical Loss Summary

Problem
A pharmacy chain wants to analyze its financial performance by identifying losses on drugs, where each drug is produced by exactly one manufacturer. A drug is loss-making when its cost of goods sold (cogs) exceeds its total sales. For each manufacturer that has at least one loss-making drug, report the number of loss-making drugs (drug_count) and the total monetary loss (total_loss) as an absolute value.

Output columns: manufacturer, drug_count, total_loss

Sort the results by total_loss in descending order.


Schema
1 table
Expand all

dls_drug_loss
6 cols
product_id
INT
units_sold
INT
total_sales
DECIMAL
cogs
DECIMAL
manufacturer
VARCHAR
drug
VARCHAR
Examples
Example 1

Input:

dls_drug_loss:

product_id	units_sold	total_sales	cogs	manufacturer	drug
156	89514	3130097	3427421.73	Biogen	Acyclovir
25	222331	2753546	2974975.36	AbbVie	Lamivudine and Zidovudine
50	90484	2521023.73	2742445.9	Eli Lilly	Dermasorb TA Complete Kit
98	110746	813188.82	140422.87	Biogen	Medi-Chord
Output:

manufacturer	drug_count	total_loss
Biogen	1	297324.73
AbbVie	1	221429.36
Eli Lilly	1	221422.17
Constraints
Handle NULL values appropriately
Return results matching the expected output schema and order

-- Write query here
-- TABLE NAME: `dls_drug_loss`

11. Duplicate Email Removal

Problem
You are given a table person that contains email addresses. Some emails may appear multiple times with different id values. Your task is to write a query that removes duplicates, keeping only the record with the smallest id for each unique email.

Output columns: id, email


Schema
1 table
Expand all

rde_person
2 cols
id
INT
email
VARCHAR
Examples
Example 1

Input:

rde_person:

id	email
1	john@example.com
2	bob@example.com
3	john@example.com
Output:

id	email
1	john@example.com
2	bob@example.com
Constraints
Handle NULL values appropriately
Return results matching the expected output schema and order

-- Write query here
-- TABLE NAME: `rde_person`

12. Student Exam Participation Report

Problem
A school wants an exam-attendance report containing every student and every offered subject, including combinations with no attendance. For each student-subject pair, return the number of matching rows in epc_examinations.

Output columns: student_id, student_name, subject_name, attended_exams


Schema
3 tables
Expand all

epc_students
2 cols
student_id
INT
student_name
VARCHAR

epc_subjects
1 col
subject_name
VARCHAR

epc_examinations
2 cols
student_id
INT
subject_name
VARCHAR
Examples
Example 1

Input:

epc_students:

student_id	student_name
1	Alice
epc_subjects:

subject_name
Math
Physics
Programming
epc_examinations:

student_id	subject_name
1	Math
1	Physics
1	Programming
1	Physics
1	Math
1	Math
Output:

student_id	student_name	subject_name	attended_exams
1	Alice	Math	3
1	Alice	Physics	2
1	Alice	Programming	1
Explanation: Alice appears three times for Math, twice for Physics, and once for Programming.

Constraints
Return one row for every student-subject combination.
Use 0 when a student has no examination row for a subject.
Order by student_id ascending, then subject_name ascending.
Return results matching the expected output schema and order.

import pandas as pd
import numpy as np
import datetime
import json
import math
import re

def etl(epc_examinations, epc_students, epc_subjects):
    pass

13. Large Country Identification
Problem
A country is considered large if it meets at least one of the following criteria: Its area is greater than or equal to 3,000,000 square kilometers. Its population is greater than or equal to 25,000,000 people. Your task is to write an SQL query to retrieve the name, population, and area of all such large countries.

Output columns: name, population, area


Schema
1 table
Expand all

bne_countries_val
5 cols
name
VARCHAR
continent
VARCHAR
area
INT
population
INT
gdp
INT
Examples
Example 1

Input:

bne_countries_val:

name	continent	area	population	gdp
Afghanistan	Asia	652230	25500100	20343000000
Albania	Europe	28748	2831741	12960000000
Algeria	Africa	2381741	37100000	188681000000
Andorra	Europe	468	78115	3712000000
Output:

name	population	area
Afghanistan	25500100	652230
Algeria	37100000	2381741
Constraints
Handle NULL values appropriately
Return results matching the expected output schema and order


from pyspark.sql import SparkSession
from pyspark.sql.functions import col

def etl(bne_countries_val):
    pass


14. Self-Viewing Authors Detection
Problem
A publishing platform records every article view. Identify authors who viewed at least one of their own articles, return each matching author once as id, and order the IDs ascending.

Output columns: id


Schema
1 table
Expand all

avow_sample
4 cols
article_id
INT
author_id
INT
viewer_id
INT
view_date
DATE
Examples
Example 1

Input:

avow_sample:

author_id	view_date	viewer_id	article_id
3	2019-08-01	5	1
3	2019-08-02	6	1
7	2019-08-01	7	2
7	2019-08-02	6	2
7	2019-07-22	1	4
4	2019-07-21	4	3
4	2019-07-21	4	3
Output:

id
4
7
Explanation: Author 4 appears twice with viewer_id 4, but the output includes ID 4 only once; author 7 also qualifies from its self-view row.

Constraints
Use every supplied input row when calculating the result.
Preserve the calculation, filtering, tie handling, and ordering described in the problem.
Return results matching the expected output schema and order.

from pyspark.sql import SparkSession
from pyspark.sql.functions import col

def etl(avow_sample):
    pass

15. Wine Selection Filter

Problem
A customer is searching for a specific wine based on its chemical characteristics. You are given a table of chemical properties for various wines. Return the IDs of all wines that meet ALL of the following criteria: alcohol content is greater than or equal to 13, ash is less than 2.4, and color intensity is less than 3.0.

Output columns: id


Schema
1 table
Expand all

wfm_wines
14 cols
id
INT
alcohol
DECIMAL
malic_acid
DECIMAL
ash
DECIMAL
alcalinity_of_ash
INT
magnesium
INT
total_phenols
DECIMAL
flavanoids
DECIMAL
nonflavanoid_phenols
DECIMAL
proanthocyanins
DECIMAL
color_intensity
DECIMAL
hue
INT
od280_or_od315_of_diluted_wines
INT
proline
INT
Examples
Example 1

Input:

wfm_wines:

id	alcohol	malic_acid	ash	alcalinity_of_ash	magnesium	total_phenols	flavanoids	nonflavanoid_phenols	proanthocyanins	color_intensity	hue	od280_or_od315_of_diluted_wines	proline
1	13.05	2.1	2.5	15	100	2.5	2.1	0.3	1.5	2.5	1	3	700
2	12.8	1.8	2.3	18	98	2.7	2.4	0.28	1.4	3.2	1	3	690
3	13.2	2.5	2.1	18	105	2.3	2	0.35	1.6	2.9	1	3	720
4	14	2.2	2.6	16	101	2.6	2.5	0.33	1.7	3.5	1	3	730
5	13.5	1.6	2.2	15	97	2.8	2.3	0.31	1.3	2.1	1	3	710
Output:

id
3
5
Constraints
Handle NULL values appropriately
Return results matching the expected output schema and order


-- Write query here
-- TABLE NAME: `wfm_wines`


16. Department Salary Sum

Problem
You are provided with a dataset containing employee information, including their individual salaries. Write a SQL query to calculate the total salary paid to all employees across the company. The output should return a single column showing the overall sum of all employee salaries.

Output columns: total_salary


Schema
1 table
Expand all

ses_salaries
6 cols
id
INT
first_name
VARCHAR
last_name
VARCHAR
salary
INT
department_id
INT
manager_id
DECIMAL
Examples
Example 1

Input:

ses_salaries:

id	first_name	last_name	salary	department_id	manager_id
1	John	Doe	50000	1	
2	Jane	Smith	60000	2	1.0
3	Alice	Johnson	55000	1	1.0
4	Bob	Brown	45000	3	2.0
Output:

total_salary
210000
Constraints
Handle NULL values appropriately
Return results matching the expected output schema and order


-- Write query here
-- TABLE NAME: `ses_salaries`


17. Highest Paid per Department
Problem
Find the top salary in every department for the compensation review.

You are a data analyst at Airbnb supporting the annual compensation review. HR wants a simple benchmark: the highest salary currently paid in each department, one row per department.

Write a query against hppd_highest_pay that groups employees by department and returns the maximum salary in each department, aliased as largest_salary. Return exactly one row per department even if several employees share the top salary. Sort the results by department in ascending alphabetical order.

Output columns: department, largest_salary


Schema
1 table
Expand all

hppd_highest_pay
3 cols
id
INT
department
VARCHAR
salary
INT
Examples
Example 1

Input:

hppd_highest_pay:

id	department	salary
1	HR	5000
2	HR	7000
3	IT	10000
4	IT	9500
5	Finance	6000
Output:

department	largest_salary
Finance	6000
HR	7000
IT	10000
Explanation: Each department contributes exactly one row carrying its maximum salary — no HR employee earns more than 7000 and no IT employee earns more than 10000, while Finance's single employee sets its maximum at 6000. Departments are listed alphabetically: Finance, HR, IT.

Constraints
Return exactly the columns department, largest_salary.
Return one row per department, even if several employees tie for the top salary.
Sort by department in ascending alphabetical order.

from pyspark.sql import functions as F
from pyspark.sql import Window as W
from pyspark.sql import SparkSession
import datetime
import json

spark = SparkSession.builder.appName('run-pyspark-code').getOrCreate()

def etl(input_df):
    pass

18. Sports Match Score Summary

Problem
A local team is analyzing their match performance over a season. For every game played, they have stored the match date, whether they won or lost, and the score difference. You are given a table named scores that holds the following information: the date of the match, the result ('Win' or 'Loss'), and the score differential.

Output columns: Date, Result, Differential, Scoreline


Schema
1 table
Expand all

mss_score
3 cols
Date
DATE
Result
VARCHAR
Differential
INT
Examples
Example 1

Input:

mss_score:

Date	Result	Differential
2023-10-01	Win	10
2023-10-08	Loss	7
2023-10-15	Win	3
Output:

Date	Result	Differential	Scoreline
2023-10-01	Win	10	Win by 10
2023-10-08	Loss	7	Loss by 7
2023-10-15	Win	3	Win by 3
Constraints
Handle NULL values appropriately
Return results matching the expected output schema and order


from pyspark.sql import SparkSession
from pyspark.sql.functions import col, concat_ws, date_format

def etl(input_df):
    pass

19. Revenue Range (Max Minus Min)

Problem
A finance team wants a quick measure of how widely sales revenue varies. Across all sales, return the largest revenue as max_revenue, the smallest as min_revenue, and their difference as revenue_difference.

Output columns: max_revenue, min_revenue, revenue_difference

max_revenue is the requested max revenue measure; min_revenue is the requested min revenue measure; revenue_difference is the requested revenue difference measure.


Schema
1 table
Expand all

sales
4 cols
sale_id
INT
region
VARCHAR
month
VARCHAR
revenue
DECIMAL
Examples
Example 1

Input:

sales:

month	region	revenue	sale_id
January	North	15000.5	1
January	South	22000.75	2
January	East	18500.25	3
January	West	19000	4
February	North	16500	5
February	South	25000	6
February	East	17500.5	7
February	West	18750.25	8
Output:

max_revenue	min_revenue	revenue_difference
25000	15000.5	9999.5
Explanation: The largest shown revenue is 25000 and the smallest is 15000.5, so revenue_difference is 25000 - 15000.5 = 9999.5.

Constraints
Use every supplied input row when calculating the result.
Preserve the calculation, filtering, tie handling, and ordering described in the problem.
Return results matching the expected output schema and order.

-- write your SQL query here

20. Active Subscription Amount Summary

Problem
A SaaS operations team needs a normalized export of active subscriptions. For each active row, return the subscription id as id, its monthly_amount as result_value, and half of that amount as metric.

Output columns: id, result_value, metric


Schema
1 table
Expand all

subscriptions
6 cols
subscription_id
INT
customer_id
INT
monthly_amount
DECIMAL
start_date
DATE
end_date
DATE
status
VARCHAR
Examples
Example 1

Input:

subscriptions:

subscription_id	customer_id	monthly_amount	start_date	end_date	status
1	101	99.00	2024-01-01	9999-12-31	active
2	102	199.00	2024-01-15	9999-12-31	active
Output:

id	result_value	metric
1	99.00	49.50
2	199.00	99.50
Explanation: Half of the two active monthly amounts is 49.50 and 99.50.

Constraints
Include only rows whose status is active.
Preserve decimal precision and round metric to two decimal places.
Sort by id ascending.
Return results matching the expected output schema and order.


from pyspark.sql import functions as F

def etl(subscriptions):
    #write solution

21. Data Cleaning - User Flags Validation

Problem
YouTube users can flag videos for content violations, but some flags arrive with missing data and must be discarded. A flag counts as valid only when its flag_type is present (not NULL) and its reason is present (not NULL and not an empty string). For every user who has at least one valid flag, report the user's id and the number of valid flags they submitted.

Output columns: user_id, valid_flag_count


Schema
1 table
Expand all

user_flags
6 cols
Examples
Example 1

Input:

user_flags:

flag_id	user_id	video_id	flag_type	reason	created_at
1	101	5001	harassment	Abusive language and threats	2024-01-15
2	101	5002	spam		2024-01-16
3	101	5003	copyright		2024-01-17
4	102	5004	harassment	Violent threats towards others	2024-01-18
5	102	5005	misinformation	Spreading false health claims	2024-01-19
6	103	5006		Inappropriate content	2024-01-20
8	104	5008	spam	Bot account spamming links	2024-01-22
Output:

user_id	valid_flag_count
102	2
101	1
104	1
Explanation: User 102's flags 4 and 5 both have a flag_type and a non-empty reason, giving a count of 2. User 101 submitted three flags, but flag 2 has a missing reason and flag 3 has an empty reason, so only flag 1 is valid (count 1). User 103's single flag has no flag_type, so user 103 is dropped entirely. Users 101 and 104 tie at 1, so the smaller id 101 comes first.

Constraints
A flag is valid only when flag_type is present and reason is present and not an empty string ('').
Users with zero valid flags do not appear in the output.
user_id is stored as text but holds numeric ids; return it as an integer.
Order by valid_flag_count descending, then by user_id ascending in numeric order.
Return results matching the expected output schema and order.

--- write SQL Query here

# Medium 


1. CRM Order Summary Report
Problem
You’re working as a Data Engineer at a company that builds Customer Relationship Management (CRM) software. Your goal is to build a unified view that shows order details along with customer and product information — useful for internal dashboards and reporting. You are given three datasets (or tables) that store customer, order, and product details.

Output columns: order_id, customer_name, customer_email, product_name, product_category, order_date

Sort the results by o.order_id ASC.


Schema
3 tables
Expand all

crm_customers
4 cols
customer_id
INT
first_name
VARCHAR
last_name
VARCHAR
email
VARCHAR

crm_orders
4 cols
order_id
INT
customer_id
INT
product_id
INT
order_date
DATE

crm_products
3 cols
product_id
INT
product_name
VARCHAR
category
VARCHAR
Examples
Example 1

Input:

crm_customers:

customer_id	first_name	last_name	email
1	John	Doe	john.doe@email.com
2	Jane	Smith	jane.smith@email.com
crm_orders:

order_id	customer_id	product_id	order_date
1001	1	101	2023-01-10
1002	2	102	2023-01-11
crm_products:

product_id	product_name	category
101	Product A	Category1
102	Product B	Category2
Output:

order_id	customer_name	customer_email	product_name	product_category	order_date
1001	John Doe	john.doe@email.com	Product A	Category1	2023-01-10
1002	Jane Smith	jane.smith@email.com	Product B	Category2	2023-01-11
Constraints
Handle NULL values appropriately
Return results matching the expected output schema and order


from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql import Window as W
import pyspark
import datetime
import json

spark = SparkSession.builder.appName('run-pyspark-code').getOrCreate()

def etl(customers, orders, products):
    # Write code here
    pass

2. F&B Product Sales Summary
Problem
A food-and-beverage retailer needs one summary row for every product, including products with no sales. Report total quantity and revenue from sales plus total stock across warehouses, using zero when a product has no matching activity.

Output columns: product_id, name, category, total_quantity, total_revenue, total_stock


Schema
3 tables
Expand all

fnb_products
3 cols
product_id
INT
name
VARCHAR
category
VARCHAR

fnb_sales
4 cols
sale_id
INT
product_id
INT
quantity
INT
revenue
DECIMAL

fnb_inventory
3 cols
product_id
INT
stock
INT
warehouse
VARCHAR
Examples
Example 1

Input:

fnb_products:

product_id	name	category
3	Chocolate Bar	Snacks
4	Potato Chips	Snacks
fnb_sales:

sale_id	product_id	quantity	revenue
4	3	2	4
5	4	15	30
fnb_inventory:

product_id	stock	warehouse
3	30	Warehouse1
4	20	Warehouse1
Output:

product_id	name	category	total_quantity	total_revenue	total_stock
3	Chocolate Bar	Snacks	2	4	30
4	Potato Chips	Snacks	15	30	20
Explanation: Each product's sales and stock are summed independently before producing its summary row.

Constraints
Include every product from fnb_products.
Replace missing sales or inventory totals with zero.
Sort by category, then product_id, both ascending.
Return results matching the expected output schema and order.

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql import Window as W
import pyspark
import datetime
import json

spark = SparkSession.builder.appName('run-pyspark-code').getOrCreate()

def etl(inventory, products, sales):
    # Write code here
    pass

3. Maximum Boarding Capacity
Problem
A group of passengers is waiting in line to board a bus. However, the bus has a maximum weight capacity of 1000 kilograms. Passengers board one at a time based on their boarding order, and the boarding process stops as soon as the next passenger would cause the total weight to exceed the limit.

Output columns: passenger_name


Schema
1 table
Expand all

mcb_sample
4 cols
passenger_id
INT
passenger_name
VARCHAR
weight_kg
INT
boarding_order
INT
Examples
Example 1

Input:

mcb_sample:

passenger_id	passenger_name	weight_kg	boarding_order
5	Alice	250	1
4	Bob	175	5
3	Alex	350	2
6	John Cena	400	3
Output:

passenger_name
John Cena
Constraints
Handle NULL values appropriately
Return results matching the expected output schema and order

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, sum as spark_sum
from pyspark.sql.window import Window

def etl(mcb_sample):
    #write your code here

4. Top Film Reviewer & Best Movie
Problem
A streaming service wants two highlights from its ratings data. Return exactly two rows in one column named results, in this order:

The full name of the viewer who submitted the most ratings across all dates. If viewers tie, choose the alphabetically smallest name.
The title of the film with the highest average rating among reviews dated from 2020-02-01 through 2020-02-29, inclusive. If films tie, choose the alphabetically smallest title.
Output columns: results


Schema
3 tables
Expand all

trb_film_ratings
4 cols
film_id
INT
viewer_id
INT
rating
INT
review_date
DATE

trb_films
2 cols
film_id
INT
title
VARCHAR

trb_viewers
2 cols
viewer_id
INT
full_name
VARCHAR
Examples
Example 1

Input:

trb_film_ratings:

film_id	viewer_id	rating	review_date
1	1	3	2020-01-12
1	2	4	2020-02-11
1	3	2	2020-02-12
1	4	1	2020-01-01
2	1	5	2020-02-17
2	2	2	2020-02-01
2	3	2	2020-03-01
3	1	3	2020-02-22
3	2	4	2020-02-25
2	4	NULL	2020-02-20
trb_films:

film_id	title
1	Avengers
2	Frozen 2
3	Joker
trb_viewers:

viewer_id	full_name
1	Daniel
2	Monica
3	Maria
4	James
Output:

results
Daniel
Frozen 2
Explanation: Daniel and Monica each submitted three ratings, so Daniel wins alphabetically; Frozen 2 and Joker both average 3.5 during February, so Frozen 2 wins the title tie-break.

Constraints
Count rating rows, not distinct films, when selecting the viewer.
Use only reviews from 2020-02-01 through 2020-02-29 for the film average.
Break viewer ties by full_name ascending and film ties by title ascending.
Return the viewer row first and the film row second.
A rating row may have a NULL rating value (score withheld): it still counts toward a viewer’s number of rated films, but is ignored when computing a film’s average rating. Viewers with no rating rows cannot be the top reviewer.
Return results matching the expected output schema and order.

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, avg, desc

def etl(trb_film_ratings, trb_films, trb_viewers):
    pass


5. Salary Outlier Detection

Problem
An HR team wants the employees at the two extremes of the company salary range. Return every employee whose salary equals the overall maximum or minimum, labeling the former Highest Salary and the latter Lowest Salary in salary_type. Include worker_id, salary, and department; if multiple employees share an extreme, return all of them.

Output columns: worker_id, salary, department, salary_type

salary is the requested salary measure; salary_type labels whether the salary is the overall maximum or minimum.


Schema
1 table
Expand all

es_extreme_salaries
6 cols
worker_id
INT
first_name
VARCHAR
last_name
VARCHAR
salary
INT
joining_date
DATE
department
VARCHAR
Examples
Example 1

Input:

es_extreme_salaries:

salary	last_name	worker_id	department	first_name	joining_date
100000	Arora	1	HR	Monika	2014-02-20
80000	Verma	2	Admin	Niharika	2014-06-11
300000	Singhal	3	HR	Vishal	2014-02-20
500000	Singh	4	Admin	Amitah	2014-02-20
500000	Bhati	5	Admin	Vivek	2014-06-11
200000	Diwan	6	Account	Vipul	2014-06-11
75000	Kumar	7	Account	Satish	2014-01-20
90000	Chauhan	8	Admin	Geetika	2014-04-11
Output:

worker_id	salary	department	salary_type
4	500000	Admin	Highest Salary
5	500000	Admin	Highest Salary
7	75000	Account	Lowest Salary
Explanation: Workers 4 and 5 both earn the overall maximum of 500000 and are labeled Highest Salary, while worker 7 earns the minimum of 75000 and is labeled Lowest Salary.

Constraints
Use every supplied input row when calculating the result.
Preserve the calculation, filtering, tie handling, and ordering described in the problem.
Return results matching the expected output schema and order.

import pandas as pd
import numpy as np
import datetime
import json
import math
import re

def etl(input_df):
    # Write code here
    pass


6. Monthly Account Closure Rate
Problem
An account-status system records one row per account per day showing whether that account was open or closed. Among the accounts that were open on December 31, 2019, find what percentage were closed on January 1, 2020. Report a single value, percentage_closed, as that percentage rounded to two decimal places.

Output columns: percentage_closed


Schema
1 table
Expand all

ACR_account_closure
3 cols
account_id
INT
date
DATE
status
VARCHAR
Examples
Example 1

Input:

acr_account_closure:

account_id	date	status
1	2019-12-31	open
1	2020-01-01	closed
2	2019-12-31	open
2	2020-01-01	open
3	2019-12-31	open
3	2020-01-01	closed
4	2019-12-31	closed
4	2020-01-01	closed
Output:

percentage_closed
66.67
Explanation: Accounts 1, 2, and 3 were open on 2019-12-31, so the denominator is 3 (account 4 was already closed that day and is excluded). Of those three, accounts 1 and 3 were closed on 2020-01-01, giving 2 / 3 = 66.67%.

Constraints
Only accounts that were open on 2019-12-31 count toward the denominator; accounts already closed on that date are excluded.
The numerator counts accounts from that group whose status was closed on 2020-01-01.
Round the percentage to two decimal places.
Return results matching the expected output schema and order.

import pandas as pd
import numpy as np
import datetime
import json
import math
import re

def etl(input_df):
    # Write code here
    pass


7. Longest Customer Visit Streaks
Problem
A product team wants to reward the most loyal visitors. Every row in tvs_event records one page visit with its timestamp. For each user, find the length of their longest streak of consecutive calendar days on which they visited at least once (multiple visits on the same day count as a single day, and any gap in dates ends the streak). Return the five users with the longest such streaks.

For each qualifying user, report:

user_id: the user
streak_length: the number of days in that user's longest run of back-to-back visit days
Output columns: user_id, streak_length


Schema
1 table
Expand all

tvs_event
3 cols
user_id
INT
created_at
TIMESTAMP
url
VARCHAR
Examples
Example 1

Input:

tvs_event:

user_id	created_at	url
1	2023-01-01 10:00:00	/home
1	2023-01-02 11:00:00	/profile
1	2023-01-04 09:30:00	/home
2	2023-01-01 08:00:00	/home
2	2023-01-02 09:15:00	/dashboard
2	2023-01-03 07:45:00	/settings
3	2023-01-10 08:00:00	/home
3	2023-01-10 20:00:00	/profile
Output:

user_id	streak_length
2	3
1	2
3	1
Explanation: User 2 visited on Jan 1, 2, and 3 with no gaps, giving a streak of 3. User 1 visited on Jan 1 and 2 (streak of 2), then skipped Jan 3, so the Jan 4 visit starts a new run and does not extend the streak. User 3 visited twice on Jan 10, which counts as a single day, so their longest streak is 1.

Constraints
Multiple visits on the same calendar day count as one day toward a streak.
A streak breaks on any missing calendar day between visits.
List users from longest streak to shortest and return only the top five.
Return results matching the expected output schema and order.

-- Write query here
-- TABLE NAME: `tvs_event`

8. Employee Career Progression Tracker
Problem
The table cpt_user_experience records every position each user has held, one row per role, with the start and end date of that role. A user is said to have made a direct move from Data Analyst to Data Scientist when their Data Scientist role immediately followed their Data Analyst role in chronological order, with no other position held in between. Report a single value percentage: the share of all users who made this direct move, out of the total number of distinct users, as a percentage rounded to two decimals.

Output columns: percentage


Schema
1 table
Expand all

cpt_user_experience
5 cols
id
INT
position_name
VARCHAR
start_date
DATE
end_date
DATE
user_id
INT
Examples
Example 1

Input:

cpt_user_experience:

id	position_name	start_date	end_date	user_id
1	Intern	2020-01-01	2020-06-01	1
2	Data Analyst	2020-06-02	2021-06-01	1
3	Data Scientist	2021-06-02	2022-06-01	1
4	Data Analyst	2020-03-01	2021-02-01	2
5	Product Manager	2021-02-02	2022-02-01	2
6	Data Scientist	2022-02-02	2023-02-01	2
7	Data Analyst	2020-05-01	2021-05-01	3
8	Data Scientist	2021-05-02	2022-05-01	3
Output:

percentage
75.00
Explanation: User 1 goes Data Analyst then Data Scientist next, and user 3 goes Data Analyst then Data Scientist next, so both count. User 2 held Product Manager between the two roles, so that move is not direct and user 2 does not count. That is 2 of 3 users, or 66.67%.

Constraints
The Data Scientist role must be the position chronologically right after the Data Analyst role for the same user, ordered by start_date.
Denominator is the count of distinct users in the table.
Round the percentage to two decimal places.
Count each user at most once in the numerator, even if they made the Data Analyst to Data Scientist transition more than once.
Return results matching the expected output schema and order.

from pyspark.sql import functions as F
from pyspark.sql import Window as W
from pyspark.sql import SparkSession
import datetime
import json

spark = SparkSession.builder.appName('run-pyspark-code').getOrCreate()

def etl(input_df):
    pass

9. Last Transaction of Each Day
Problem
A table dlt_daily_last records every transaction made at a bank, with a unique id, the transaction amount, and the timestamp when it occurred. For each calendar day, find the single transaction that happened latest on that day. Return that transaction's timestamp, its amount, and its id, one row per day.

Output columns: created_at, transaction_value, id

Sort the results by created_at.


Schema
1 table
Expand all

dlt_daily_last
3 cols
id
INT
created_at
TIMESTAMP
transaction_value
DECIMAL
Examples
Example 1

Input:

dlt_daily_last:

id	created_at	transaction_value
101	2023-01-01 09:00:00	150.75
102	2023-01-01 12:30:00	200.5
103	2023-01-01 17:45:00	175.2
104	2023-01-02 10:15:00	80
105	2023-01-02 23:59:59	90.5
106	2023-01-03 08:00:00	120
Output:

created_at	transaction_value	id
2023-01-01 17:45:00	175.2	103
2023-01-02 23:59:59	90.5	105
2023-01-03 08:00:00	120	106
Explanation: On 2023-01-01 three transactions occurred (09:00, 12:30, 17:45); the latest is id 103 at 17:45:00 with amount 175.2, so that is the only 2023-01-01 row returned. 2023-01-02 keeps id 105 at 23:59:59 over the earlier 10:15 transaction, and 2023-01-03 has a single transaction, id 106.

Constraints
Each calendar day contributes exactly one row: the transaction with the latest timestamp on that day.
The timestamp is formatted as YYYY-MM-DD HH24:MI:SS.
Return results matching the expected output schema and order.

-- Write query here
-- TABLE NAME: `dlt_daily_last`

10. Repeat Customer Identification
Problem
A commerce team wants the number of users who purchased again on a later calendar date than their first purchase. Return this distinct-user count as num_of_upsold_customers; multiple purchases on the first date alone do not qualify.

Output columns: num_of_upsold_customers


Schema
1 table
Expand all

st_transactions
5 cols
id
INT
user_id
INT
created_at
TIMESTAMP
product_id
INT
quantity
INT
Examples
Example 1

Input:

st_transactions:

id	user_id	created_at	product_id	quantity
1	10	2024-01-01T10:00:00	100	1
2	10	2024-01-01T18:00:00	200	1
3	10	2024-01-03T09:00:00	300	1
4	20	2024-02-01T10:00:00	100	2
5	30	2024-03-01T10:00:00	100	1
6	30	2024-03-05T10:00:00	100	1
Output:

num_of_upsold_customers
2
Explanation: Users 10 and 30 each purchase on a date after their first purchase date, while user 20 purchases only once. The distinct qualifying-user count is therefore 2.

Constraints
Purchase timestamps are compared by calendar date.
Each qualifying user contributes once to the result.
Count each customer at most once: a user who makes several purchases on days after their first purchase date still contributes 1 to num_of_upsold_customers.
Return results matching the expected output schema and order.

-- Write query here
-- TABLE NAME: `st_transactions`


11. Consistent Monthly Shoppers
Problem
You're working with transaction and user records for an online store. Your goal is to identify loyal customers who made at least 4 transactions in both 2019 and 2020. Only users who meet this threshold in each of those years should appear in the final result.

Output columns: customer_name


Schema
2 tables
Expand all

csf_users
2 cols
id
INT
name
VARCHAR

csf_transactions
5 cols
id
INT
user_id
INT
created_at
TIMESTAMP
product_id
INT
quantity
INT
Examples
Example 1

Input:

csf_users:

id	name
101	Alice
102	Bob
103	Charlie
104	David
csf_transactions:

id	user_id	created_at	product_id	quantity
1	101	2019-01-10 10:00:00	501	1
10	102	2020-02-15 10:00:00	510	1
11	103	2020-03-01 11:00:00	511	2
12	103	2020-05-01 14:00:00	512	1
13	103	2020-07-01 16:00:00	513	2
14	103	2020-08-01 18:00:00	514	1
15	104	2019-06-15 10:00:00	515	1
16	104	2019-07-15 10:00:00	516	1
17	104	2019-08-15 10:00:00	517	1
18	104	2020-06-15 10:00:00	518	1
19	104	2020-07-15 10:00:00	519	1
2	101	2019-03-15 12:00:00	502	2
20	104	2020-08-15 10:00:00	520	1
3	101	2019-05-20 09:30:00	503	1
4	101	2019-09-10 14:45:00	504	1
5	101	2020-01-05 10:00:00	505	1
6	101	2020-04-10 11:30:00	506	1
7	101	2020-07-20 15:00:00	507	1
8	101	2020-11-25 16:20:00	508	1
9	102	2019-02-15 10:00:00	509	1
Output:

customer_name
Eve
Alice
Constraints
Transactions may reference user_ids that have no matching row in csf_users (deleted accounts); such users must not appear in the result.

Handle NULL values appropriately

Return results matching the expected output schema and order

-- Write query here
-- TABLE NAME: `csf_users & csf_transactions`


12. Top Traffic Source Devices
Problem
A network team is analyzing packets captured from 2022-01-01 00:00:00 inclusive through 00:10:00 exclusive. For each ssid, count packets per device and return the largest device count as max_number_of_packages_sent.

Output columns: ssid, max_number_of_packages_sent

max_number_of_packages_sent is the largest per-device packet count for the network.


Schema
1 table
Expand all

tdf_packet_rates
5 cols
packet_id
INT
ssid
VARCHAR
mac_address
VARCHAR
time_captured
TIMESTAMP
packet_size
INT
Examples
Example 1

Input:

tdf_packet_rates:

ssid	packet_id	mac_address	packet_size	time_captured
Network_A	1	AA:BB:CC:11:22:33	150	2022-01-01T00:01:00
Network_A	2	AA:BB:CC:11:22:33	150	2022-01-01T00:02:30
Network_A	3	DD:EE:FF:44:55:66	150	2022-01-01T00:03:15
Network_A	4	AA:BB:CC:11:22:33	150	2022-01-01T00:05:00
Network_B	5	11:22:33:44:55:66	200	2022-01-01T00:04:00
Network_B	6	11:22:33:44:55:66	200	2022-01-01T00:07:00
Network_B	7	77:88:99:00:AA:BB	200	2022-01-01T00:06:00
Network_A	8	DD:EE:FF:44:55:66	150	2022-01-01T00:15:00
Output:

ssid	max_number_of_packages_sent
Network_A	3
Network_B	2
Explanation: On Network_A, device AA:BB:CC:11:22:33 sends three packets before 00:10, more than any other device; the packet at 00:15 is outside the interval.

Constraints
Use every supplied input row when calculating the result.
Preserve the calculation, filtering, tie handling, and ordering described in the problem.
Return results matching the expected output schema and order.

-- Write query here
-- TABLE NAME: `tdf_packet_rates`


13. Second Purchase Amount and Time Gap
Problem
A retention team wants to understand how quickly customers make a repeat purchase. Order each customer's purchases by order_date, breaking same-day ties by order_id. For every customer with at least two orders, return the amount of their second order and the number of calendar days between their first and second orders.

Output columns: id, result_value, metric

id is the customer id.
result_value is the second order's amount, returned as an integer.
metric is the number of days from the first order date to the second order date.

Schema
1 table
Expand all

orders
4 cols
order_id
INT
customer_id
INT
order_date
DATE
amount
DECIMAL
Examples
Example 1

Input:

orders:

order_id	customer_id	order_date	amount
1	101	2024-01-05	50
2	101	2024-01-20	75
3	101	2024-02-10	100
4	102	2024-01-15	60
5	102	2024-02-05	90
Output:

id	result_value	metric
101	75	15
102	90	21
Explanation: Customer 101's second order is 75 and occurs 15 days after their first; customer 102's second order is 90 and occurs 21 days after their first.

Constraints
Exclude customers with fewer than two orders.
Order purchases by order_date ascending, then order_id ascending.
Use only the first and second purchases when calculating metric.
Order results by id ascending.
Return results matching the expected output schema and order.

from pyspark.sql import functions as F
from pyspark.sql.window import Window

def etl(orders):
    #write code here

14. Deduplication with Composite Key
Problem
A cleanup job keeps one record for each (user_id, product_id) pair. Keep the record with the smallest record_id, return its amount, and derive metric by dividing that integer amount by 2 with any fractional remainder discarded.

Output columns: id, result_value, metric

Keep the smallest record_id within each user-product pair.
result_value is the retained amount; metric is integer division amount / 2, truncated toward zero.
Order by retained id ascending.

Schema
1 table
Expand all

records
5 cols
record_id
INT
user_id
INT
product_id
INT
order_date
DATE
amount
INTEGER
Examples
Example 1

Input:

records:

record_id	user_id	product_id	order_date	amount
1	101	1	2024-01-01	100
2	101	1	2024-01-01	100
3	101	2	2024-01-01	50
4	101	2	2024-01-01	50
5	102	1	2024-01-05	100
6	102	1	2024-01-05	100
7	102	1	2024-01-05	100
8	102	3	2024-01-10	75
9	103	2	2024-01-15	50
10	103	3	2024-01-20	75
11	103	3	2024-01-20	75
12	104	1	2024-02-01	100
13	104	2	2024-02-01	50
14	104	2	2024-02-01	50
15	105	3	2024-02-05	75
Output:

id	result_value	metric
1	100	50
3	50	25
5	100	50
8	75	37
9	50	25
10	75	37
12	100	50
13	50	25
15	75	37
Explanation: Record 8 is the retained row for its user-product pair, and integer division turns its amount of 75 into metric 37.

Constraints
Keep the smallest record_id within each user-product pair.
result_value is the retained amount; metric is integer division amount / 2, truncated toward zero.
Order by retained id ascending.
Return results matching the expected output schema and order.

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
import datetime

spark = SparkSession.builder.appName('run-pyspark-code').getOrCreate()

def etl(records):
    # DataFrame operations here
    pass


15. Find N-th Record in Each Group
Problem
Find the N-th record in each group without using LIMIT. Use window functions to access specific row positions. For this problem N = 3: return the 3rd record of each group. Groups with fewer than 3 records are excluded.

Output columns: customer_id, transaction_id, amount, row_num

Sort results by customer_id, row_num.


Schema
1 table
Expand all

transactions
4 cols
transaction_id
INT
customer_id
INT
amount
NUMERIC
transaction_date
DATE
Examples
Example 1

Input:

transactions:

transaction_id	customer_id	amount	transaction_date
1	101	250.00	2024-01-05
2	101	120.50	2024-01-10
3	101	430.75	2024-01-15
4	101	200.00	2024-01-20
5	102	90.00	2024-02-01
6	102	60.25	2024-02-03
7	103	500.00	2024-03-01
8	103	150.00	2024-03-05
9	103	320.40	2024-03-09
10	103	275.00	2024-03-12
11	103	410.00	2024-03-15
12	104	999.99	2024-04-01
Output:

customer_id	transaction_id	amount	row_num
101	3	430.75	3
103	9	320.40	3
Explanation: Records are partitioned by customer_id, ordered by transaction_id, and numbered within each partition. Only the 3rd record (row_num = 3) of each customer is returned. Customer 101 (4 records) and customer 103 (5 records) each have a 3rd record, so those rows are included. Customer 102 (2 records) and customer 104 (1 record) have fewer than 3 records, so they are excluded entirely.

Constraints
N larger than group size (customer is excluded from output)
N=0 or negative (no records returned)
Single record per group (excluded if N > 1)

from pyspark.sql import functions as F
from pyspark.sql.window import Window

def etl(transactions):
    #write your code here

16. Moving Sum vs Moving Average Comparison
Problem
Compare a moving sum against a moving average using window functions with a ROWS frame. For each day, compute the 3-day moving sum and the 3-day moving average of revenue, where the window covers the current row and the two preceding rows.

Output columns: date, amount, moving_sum_3day, moving_avg_3day

Sort the results by date.


Schema
1 table
Expand all

daily_revenue
2 cols
revenue_date
DATE
amount
INT
Examples
Example 1

Input:

daily_revenue:

revenue_date	amount
2024-01-01	1000
2024-01-02	1200
2024-01-03	1100
2024-01-04	1300
2024-01-05	1250
2024-01-06	1400
2024-01-07	1350
2024-01-08	1500
2024-01-09	1450
2024-01-10	1600
Output:

date	amount	moving_sum_3day	moving_avg_3day
2024-01-01	1000.0	1000	1000.0
2024-01-02	1200.0	2200	1100.0
2024-01-03	1100.0	3300	1100.0
2024-01-04	1300.0	3600	1200.0
2024-01-05	1250.0	3650	1216.67
2024-01-06	1400.0	3950	1316.67
2024-01-07	1350.0	4000	1333.33
2024-01-08	1500.0	4250	1416.67
2024-01-09	1450.0	4300	1433.33
2024-01-10	1600.0	4550	1516.67
Constraints
Handle NULL values appropriately
Return results matching the expected output schema and order

--- write SQL Query here
SELECT
  -- columns here
FROM
  -- tables here
WHERE
  -- filters here


17. Correlated Subquery for Running Calculations
Problem
A retail team keeps one row per day with that day's total sales. For every day, report the sales recorded on that day alongside a cumulative total that adds up all sales from the earliest day through the current day. Return one row per day with these columns: date (the sale date), sales_amount (the sales total recorded on that date), and running_sum (the cumulative total of sales_amount from the earliest date up to and including the current date).

Sort results by date.


Schema
1 table
Expand all

daily_sales
2 cols
sale_date
DATE
amount
NUMERIC
Examples
Example 1

Input:

daily_sales:

sale_date	amount
2024-01-01	100
2024-01-02	150
2024-01-03	120
2024-01-04	200
2024-01-05	180
Output:

date	sales_amount	running_sum
2024-01-01	100	100
2024-01-02	150	250
2024-01-03	120	370
2024-01-04	200	570
2024-01-05	180	750
Explanation: On 2024-01-03 the day's sales_amount is 120, and running_sum is 370 because it adds that day's 120 to the earlier days' 100 and 150. By 2024-01-05 the running_sum reaches 750 (100 + 150 + 120 + 200 + 180).

Constraints
running_sum for a day includes that day's sales_amount plus every earlier day.
Sort output ascending by date.
Return results matching the expected output schema and order.

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
import datetime

spark = SparkSession.builder.appName('run-pyspark-code').getOrCreate()

def etl(daily_sales):

    return daily_sales


# Hard

1. Property Rental Revenue Analysis
Problem
A property manager wants the total monthly rent represented by each landlord's portfolio. For every landlord with at least one property, return the landlord id, full name, and the sum of rent across all their properties.

Output columns: landlord_id, landlord_name, total_rental_income


Schema
2 tables
Expand all

prop_landlords
5 cols
landlord_id
INT
first_name
VARCHAR
last_name
VARCHAR
email
VARCHAR
phone
VARCHAR

prop_properties
6 cols
property_id
INT
landlord_id
INT
property_type
VARCHAR
rent
INT
square_feet
INT
city
VARCHAR
Examples
Example 1

Input:

prop_landlords:

landlord_id	first_name	last_name	email	phone
101	John	Smith	john.smith@example.com	555-123-4567
103	Bob	Johnson	bob.johnson@example.com	555-345-6789
prop_properties:

property_id	landlord_id	property_type	rent	square_feet	city
1	101	Apartment	1500	1000	Seattle
2	101	Condo	1200	800	Seattle
4	103	Apartment	1800	1200	Redmond
5	103	Condo	1000	700	Redmond
Output:

landlord_id	landlord_name	total_rental_income
101	John Smith	2700
103	Bob Johnson	2800
Explanation: Bob Johnson's two properties contribute 1800 + 1000 = 2800 in total rent.

Constraints
Include only landlords with at least one property.
Build landlord_name as first name, one space, then last name.
Order results by landlord_id ascending.
Return results matching the expected output schema and order.

import org.apache.spark.sql.DataFrame
import org.apache.spark.sql.functions._
import org.apache.spark.sql.expressions.Window

def etl(prop_landlords: DataFrame, prop_properties: DataFrame): DataFrame = {
}


2. Manufacturing Defect Rate Analysis

Problem
A manufacturing analytics team wants to see how each product ranks by revenue within its own category.

For every product that has a matching sales record, report the product's category, its name, its sale revenue rounded to the nearest whole number, and its rank inside that category.
Rank 1 is the product with the highest revenue in the category; products with equal revenue share the same rank and the next rank is skipped accordingly.
Products with no sales record do not appear.
Output columns: category, product_name, rank, revenue

Sort the results by category, rank.


Schema
2 tables
Expand all

manufacture_product
3 cols
product_id
INT
category
VARCHAR
product_name
VARCHAR

manufacture_sales
4 cols
sale_id
INT
product_id
INT
quantity
INT
revenue
DECIMAL
Examples
Example 1

Input:

manufacture_product:

product_id	category	product_name
1	A	Product1
2	A	Product2
3	A	Product3
4	B	Product4
5	B	Product5
6	B	Product6
manufacture_sales:

sale_id	product_id	quantity	revenue
1	1	12	180
2	2	8	120
3	3	10	120
4	4	7	69.6
6	6	5	50
Output:

category	product_name	rank	revenue
A	Product1	1	180
A	Product2	2	120
A	Product3	2	120
B	Product4	1	70
B	Product6	2	50
Explanation: In category A, Product1 has the highest revenue (180) so it ranks 1, while Product2 and Product3 both earn 120 and therefore share rank 2. In category B, Product4's revenue of 69.6 rounds to 70 and ranks above Product6 at 50; Product5 has no sales record, so it is left out entirely.

Constraints
Revenue is rounded to the nearest whole number.
Within each category, products are ranked by revenue from highest to lowest; products with the same revenue share a rank and the next rank is skipped.
Only products that have a matching sales record are included.
Products that tie on revenue within a category share the same rank position. Products with no recorded sales must not appear in the output.
Return results matching the expected output schema and order.

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql import Window as W
import pyspark
import datetime
import json

spark = SparkSession.builder.appName('run-pyspark-code').getOrCreate()

def etl(products, sales):
    # Write code here
    pass
