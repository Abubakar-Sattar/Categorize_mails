import mailbox
import email
from email.header import decode_header, make_header
import psycopg2

def extract_emails_from_mbox(mbox_path):
    mbox = mailbox.mbox(mbox_path)
    emails = []
    for message in mbox:
        emails.append(message)
    return emails

def decode_payload(payload):
    for encoding in ['utf-8', 'latin-1', 'ascii']:
        try:
            return payload.decode(encoding)
        except (UnicodeDecodeError, AttributeError):
            continue
    return payload  # If all decoding attempts fail, return raw payload

def decode_header_value(header):
    if header is None:
        return None
    if isinstance(header, str):
        return header
    decoded_header = decode_header(header)
    return str(make_header(decoded_header))

def parse_email(email_message):
    from_email = decode_header_value(email_message.get('From'))
    to_email = decode_header_value(email_message.get('To'))
    subject = decode_header_value(email_message.get('Subject'))
    mailtext = ''
    if email_message.is_multipart():
        for part in email_message.walk():
            if part.get_content_type() == 'text/plain':
                mailtext += decode_payload(part.get_payload(decode=True))
    else:
        mailtext = decode_payload(email_message.get_payload(decode=True))
    
    return from_email, to_email, subject, mailtext

def connect_to_db():
    return psycopg2.connect(
        dbname='email_db',
        user='email_user',
        password='admin',
        host='localhost',
        port='5432'
    )

def create_tables(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS emails (
                id SERIAL PRIMARY KEY,
                from_email TEXT,
                to_email TEXT,
                subject TEXT,
                mailtext TEXT
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS mailerrors (
                id SERIAL PRIMARY KEY,
                email_address TEXT UNIQUE,
                domain TEXT,
                error_count INT DEFAULT 1
            );
        """)
        conn.commit()

def insert_email_data(conn, email_data):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO emails (from_email, to_email, subject, mailtext)
            VALUES (%s, %s, %s, %s)
        """, email_data)
        conn.commit()

def update_mailerrors(conn, email_address, domain):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO mailerrors (email_address, domain)
            VALUES (%s, %s)
            SET error_count = mailerrors.error_count + 1;
        """, (email_address, domain))
        conn.commit()

def extract_domain(email_address):
    if not email_address:
        return None
    return email_address.split('@')[-1]

def handle_mail_errors(emails):
    mail_errors = []
    for email_data in emails:
        from_email, to_email, subject, mailtext = email_data
        if 'mailer-daemon' in from_email.lower():
            domain = extract_domain(to_email)
            mail_errors.append((to_email, domain))
    return mail_errors

def group_emails_by_domain(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT to_email, COUNT(*)
            FROM emails
            WHERE to_email LIKE '%@wu-tang.eu' AND from_email NOT LIKE 'mailer-daemon%'
            GROUP BY to_email;
        """)
        rows = cur.fetchall()
        return rows

def process_emails(emails):
    parsed_emails = [parse_email(email) for email in emails]

    # Connect to the PostgreSQL database
    conn = connect_to_db()

    # Create tables
    create_tables(conn)

    # Insert parsed email data into the database
    for email_data in parsed_emails:
        insert_email_data(conn, email_data)

    # Handle mail errors and insert into mailerrors table
    mail_errors = handle_mail_errors(parsed_emails)
    for email_address, domain in mail_errors:
        update_mailerrors(conn, email_address, domain)

    # Group emails by domain
    grouped_emails = group_emails_by_domain(conn)

    # Output the results
    print("Count of emails grouped by wu-tang.eu email addresses:")
    total_emails = 0
    for row in grouped_emails:
        to_email, count = row
        print(f"{to_email}: {count} emails")
        total_emails += count

    print("\nTotal number of emails sent to wu-tang.eu addresses:", total_emails)

    # Close the database connection
    conn.close()

# Paths
mbox_path = 'mails.mbox'

# Extract the Emails from the mbox file
emails = extract_emails_from_mbox(mbox_path)

# Process emails
process_emails(emails)
