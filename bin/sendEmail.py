# Send an HTML email with an embedded image and a plain text message for
# email clients that don't want to display the HTML.

from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEImage import MIMEImage
from email.MIMEBase import MIMEBase
import sys
import smtplib
import datetime

def sendEmail(strFrom, strTo, subject, message, smtpServer):

    # Create the root message and fill in the from, to, and subject headers
    #msgRoot = MIMEMultipart('related')
    msgRoot = MIMEMultipart()
    msgRoot['Subject'] = subject
    msgRoot['From'] = strFrom
    msgRoot['To'] = strTo
    msgRoot.preamble = 'This is a multi-part message in MIME format.'

    # Encapsulate the plain and HTML versions of the message body in an
    # 'alternative' part, so message agents can decide which they want to display.
    msgAlternative = MIMEMultipart('alternative')

    #msgText = MIMEText(message["text"])
    #msgAlternative.attach(msgText)

    msgText = MIMEText("<pre>" + message["text"] + "</pre>", "html")
    msgAlternative.attach(msgText)

    #msgText = MIMEText(message["html"], 'html')
    #msgAlternative.attach(msgText)

    msgRoot.attach(msgAlternative)

    attachment_html = "<html><head><title>%s</title></head><body>%s</body></html>" % (subject, message["html"])
    part = MIMEBase('text', "html")
    part.set_payload( attachment_html )
    part.add_header('Content-Disposition', \
        'attachment; filename="report_%s.html"' % datetime.datetime.now().\
        strftime('%Y_%m_%d'))
    msgRoot.attach(part) #culprit?
    attachment_csv = message["csv"]
    part = MIMEBase('text', "csv")
    part.set_payload( attachment_csv )
    part.add_header('Content-Disposition', \
        'attachment; filename="report_%s.csv"' % datetime.datetime.now().\
        strftime('%Y_%m_%d'))
    msgRoot.attach(part)
    msgRoot = msgRoot.as_string()

    # Send the email (this example assumes SMTP authentication is required)
    smtp = smtplib.SMTP()
    smtp.connect(smtpServer)
    smtp.sendmail(strFrom, strTo.split(","), msgRoot)
    smtp.quit()
