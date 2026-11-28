import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

doc = docx.Document()

# Set margins
for section in doc.sections:
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)

def add_section_heading(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(text)
    run.bold = True
    run.font.name = 'Calibri'
    run.font.size = Pt(12)
    run.font.color.rgb = RGBColor(0, 51, 102)
    return p

# Header / Contact Info
p_name = doc.add_paragraph()
p_name.paragraph_format.space_after = Pt(2)
run_name = p_name.add_run('VINOD KUMAR YERRABALLI')
run_name.bold = True
run_name.font.name = 'Calibri'
run_name.font.size = Pt(18)
run_name.font.color.rgb = RGBColor(0, 51, 102)

p_contact = doc.add_paragraph()
p_contact.paragraph_format.space_after = Pt(12)
run_contact = p_contact.add_run('Bengaluru, India (Open to Hyderabad) | +91 6304340335 | vinodkumar9676150@gmail.com\nlinkedin.com/in/vinod-kumar-yerraballi | github.com/Vinodkumar-yerraballi')
run_contact.font.name = 'Calibri'
run_contact.font.size = Pt(10)
run_contact.font.color.rgb = RGBColor(80, 80, 80)

# Summary
add_section_heading('PROFESSIONAL SUMMARY')
p_sum = doc.add_paragraph('Data & Pricing Analytics Professional with an M.Sc. in Applied Mathematics & Statistics and proven expertise in quantitative modeling, portfolio optimization, margin improvement, and automated reporting. Demonstrated success in developing analytical frameworks for price leakage, cost reduction, product mix analysis, and demand forecasting using SQL, Python, Power BI, and Tableau. Adept at partnering with cross-functional stakeholders to translate complex datasets into actionable commercial recommendations that drive profitability.')
p_sum.paragraph_format.space_after = Pt(8)

# Core Competencies
add_section_heading('CORE COMPETENCIES & ATS KEYWORDS')
competencies = [
    ('Analytics & Commercial Modeling: ', 'Price & Product Portfolio Optimization, Profitability & Margin Improvement, Cost Reduction & Variance Analysis, Price Leakage & Elasticity, Demand & PPV Forecasting, Predictive Modeling, Exploratory Data Analysis.'),
    ('Technical Stack: ', 'SQL (CTEs, Window Functions, Stored Procedures, Query Optimization), Python (Pandas, NumPy, scikit-learn, XGBoost), R, Snowflake, Databricks, Power Automate, KNIME, Advanced MS Excel.'),
    ('BI & Data Visualization: ', 'Power BI (DAX, Power Query), Tableau, Interactive Executive Dashboards, KPI Reporting, Data Visualization.'),
    ('Data Engineering & Governance: ', 'ETL/ELT Pipelines, Data Ingestion & Cleansing, AWS S3, Star Schema Data Modeling, Automated Data Reconciliation, Data Quality Checks & Lineage.')
]
for title, desc in competencies:
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.space_after = Pt(3)
    r1 = p.add_run(title)
    r1.bold = True
    r2 = p.add_run(desc)

# Experience
add_section_heading('PROFESSIONAL EXPERIENCE')

p_exp1 = doc.add_paragraph()
p_exp1.paragraph_format.space_before = Pt(6)
p_exp1.paragraph_format.space_after = Pt(2)
r_title = p_exp1.add_run('Rubick.AI  |  Associate – Data Crawling & Analytics Pipelines')
r_title.bold = True
r_title.font.size = Pt(11)
r_date = p_exp1.add_run('\t\tAug 2026 – Present')
r_date.font.size = Pt(10)
r_date.font.color.rgb = RGBColor(80, 80, 80)

bullets_exp1 = [
    'Architected and automated scalable data pipelines processing 50,000+ records per cycle across 15+ sources into standardized JSON/CSV schemas, publishing directly to AWS S3 with 100% automated ingestion and zero manual handling.',
    'Engineered multi-source data validation and reconciliation protocols, successfully reducing data quality escalations and record discrepancies by 20%.',
    'Partnered with product and commercial stakeholders to translate business requirements into audit-ready analytical outputs, accelerating delivery turnaround time by 25% and eliminating downstream rework.'
]
for b in bullets_exp1:
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.space_after = Pt(3)
    p.add_run(b)

p_exp2 = doc.add_paragraph()
p_exp2.paragraph_format.space_before = Pt(6)
p_exp2.paragraph_format.space_after = Pt(2)
r_title2 = p_exp2.add_run('The Spark Foundation  |  Machine Learning Intern')
r_title2.bold = True
r_title2.font.size = Pt(11)
r_date2 = p_exp2.add_run('\t\tOct 2022 – Nov 2022')
r_date2.font.size = Pt(10)
r_date2.font.color.rgb = RGBColor(80, 80, 80)

bullets_exp2 = [
    'Validated and refined 5+ predictive models (classification, regression, clustering), optimizing feature engineering workflows to achieve a 90% average out-of-sample prediction accuracy.',
    'Diagnosed root causes of data anomalies and engineered corrective transformation logic, enhancing overall pipeline reliability and analytical data accuracy.'
]
for b in bullets_exp2:
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.space_after = Pt(3)
    p.add_run(b)

# Projects
add_section_heading('KEY PROJECTS')

projects = [
    ('Pricing & Margin Optimization Analytical Model (Python, SQL, Pandas)', [
        'Developed portfolio-level pricing and margin improvement models analyzing price variance, cost reduction opportunities, and product mix elasticity.',
        'Automated recurring reporting workflows using Python and SQL to identify price leakage points, improving commercial margin visibility by 18%.'
    ]),
    ('Automated Job Matching & Resume Optimization Engine (Python, Playwright, LLM APIs, SQL)', [
        'Developed an end-to-end Python automation engine processing 20+ daily job listings, scoring resume alignment against target ATS keyword criteria, and automating profile updates.',
        'Integrated Gemini and Ollama LLMs for automated skill taxonomy alignment and resume tailoring, increasing ATS keyword match rates to 92%+.'
    ]),
    ('Customer Feedback NLP & Commercial Power BI Dashboard (Python, SQL, Power BI, DAX)', [
        'Engineered an advanced NLP text-classification pipeline for customer sentiment and feedback data (preprocessing, feature engineering, evaluation), lifting classification accuracy by 25%.',
        'Designed interactive Power BI executive dashboards using DAX and Power Query on cleaned multi-source datasets, boosting reporting efficiency and stakeholder decision speed by 30%.'
    ])
]

for proj_title, proj_bullets in projects:
    p_proj = doc.add_paragraph()
    p_proj.paragraph_format.space_before = Pt(4)
    p_proj.paragraph_format.space_after = Pt(2)
    r_pt = p_proj.add_run(proj_title)
    r_pt.bold = True
    r_pt.font.size = Pt(10.5)
    for b in proj_bullets:
        p = doc.add_paragraph(style='List Bullet')
        p.paragraph_format.space_after = Pt(2)
        p.add_run(b)

# Education
add_section_heading('EDUCATION')
edu = [
    'M.Sc. Mathematics (Applied Mathematics & Statistics) | Yogi Vemana University, Kadapa (Dec 2022)',
    'B.Sc. Mathematics | Yogi Vemana University, Kadapa (May 2019)'
]
for e in edu:
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.space_after = Pt(3)
    p.add_run(e)

doc.save('Vinod_Kumar_Yerraballi_Resume.docx')
print('Successfully generated Vinod_Kumar_Yerraballi_Resume.docx')
