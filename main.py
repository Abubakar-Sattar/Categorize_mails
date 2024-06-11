import mailbox
import email
from email.header import decode_header, make_header
from collections import defaultdict

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
    in_reply_to = decode_header_value(email_message.get('In-Reply-To'))
    references = decode_header_value(email_message.get('References'))
    message_id = decode_header_value(email_message.get('Message-ID'))
    
    if email_message.is_multipart():
        for part in email_message.walk():
            if part.get_content_type() == 'text/plain':
                mailtext += decode_payload(part.get_payload(decode=True))
    else:
        mailtext = decode_payload(email_message.get_payload(decode=True))
    
    return from_email, to_email, subject, mailtext, in_reply_to, references, message_id

def save_emails_to_file(emails, file_path):
    with open(file_path, 'w', encoding='utf-8') as f:
        for email_data in emails:
            from_email, to_email, subject, mailtext, in_reply_to, references, message_id = email_data
            f.write(f"From: {from_email}\n")
            f.write(f"To: {to_email}\n")
            f.write(f"Subject: {subject}\n")
            f.write(f"Message-ID: {message_id}\n")
            f.write(f"In-Reply-To: {in_reply_to}\n")
            f.write(f"References: {references}\n")
            f.write(f"Mail Text:\n{mailtext}\n")
            f.write("="*80 + "\n")

# Paths
mbox_path = 'mails.mbox'
answered_emails_file = 'answered_emails.txt'
unanswered_emails_file = 'unanswered_emails.txt'

# Step 1: Extract the Emails from the mbox file
emails = extract_emails_from_mbox(mbox_path)
parsed_emails = [parse_email(email) for email in emails]

# Step 2: Categorize Answered and Unanswered Emails
answered_emails = []
unanswered_emails = []
email_threads = {}

# Identify replied emails
for email_data in parsed_emails:
    from_email, to_email, subject, mailtext, in_reply_to, references, message_id = email_data
    email_threads[message_id] = email_data
    
    if in_reply_to or references:
        # Email is a reply
        answered_emails.append(email_data)
    elif subject and 're:' in subject.lower():
        # Subject indicates a reply
        answered_emails.append(email_data)
    else:
        # Initially mark as unanswered
        unanswered_emails.append(email_data)

# Verify unanswered emails by cross-referencing message IDs
final_unanswered_emails = []
for email_data in unanswered_emails:
    from_email, to_email, subject, mailtext, in_reply_to, references, message_id = email_data
    replied = False
    
    # Check if this email is referenced by any other email
    for ref_message_id, ref_email_data in email_threads.items():
        _, _, _, _, ref_in_reply_to, ref_references, _ = ref_email_data
        if (ref_in_reply_to and message_id in ref_in_reply_to) or (ref_references and message_id in ref_references):
            replied = True
            break

    if replied:
        answered_emails.append(email_data)
    else:
        final_unanswered_emails.append(email_data)

# Save emails to files
save_emails_to_file(answered_emails, answered_emails_file)
save_emails_to_file(final_unanswered_emails, unanswered_emails_file)

# Output results
print(f"Answered emails saved to {answered_emails_file}")
print(f"Unanswered emails saved to {unanswered_emails_file}")
