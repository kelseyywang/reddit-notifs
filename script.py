import praw
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import secrets

SUBREDDIT_TO_EXPLORE = 'askreddit'
NUM_POSTS_TO_EXPLORE = 10
SCORE_WEIGHT = 3
COMMENT_WEIGHT = 1
# The following is the minimum relevant weighted score to be a match, 
# where weighted score = SCORE_WEIGHT * score + COMMENT_WEIGHT * num comments
MIN_RELEVANT_WEIGHTED_SCORE = 20
# The following tuple contains 1. list of required terms/stems, 2. list of secondary terms, 
# 3. min number of secondary terms needed to be a match
KEYWORDS_GROUP = (['conspiracy'], ['true', 'crazy', 'real'], 1)

# Returns a count of secondary terms if is relevant, -1 otherwise
def get_keyword_count(str):
    keyword_count = 0
    required, secondary, min_secondary = KEYWORDS_GROUP
    for required_term in required:
        if required_term not in str:
            return -1
    for secondary_term in secondary:
        if secondary_term in str:
            # A secondary term was found, so add to keyword_count
            keyword_count += 1
    if keyword_count < min_secondary:
        return -1
    return keyword_count

# Returns tuples containing keyword count, weighted score, post info dict of matching posts
def get_reddit_posts():
    # Authenticate
    reddit = praw.Reddit(client_id=secrets.MY_CLIENT_ID,
                         client_secret=secrets.MY_CLIENT_SECRET,
                         user_agent=secrets.MY_USER_AGENT,
                         username=secrets.MY_REDDIT_USERNAME,
                         password=secrets.MY_REDDIT_PASSWORD)
    # Designate subreddit to explore
    subreddit = reddit.subreddit(SUBREDDIT_TO_EXPLORE)
    matching_posts_info = []
    # Explore rising posts in subreddit and store info if is relevant and popular enough
    # Tip: You could also explore top posts, new posts, etc.
    # See https://praw.readthedocs.io/en/latest/getting_started/quick_start.html#obtain-submission-instances-from-a-subreddit
    for submission in subreddit.rising(limit=NUM_POSTS_TO_EXPLORE):
        keyword_count = get_keyword_count(submission.title.lower())
        weighted_score = SCORE_WEIGHT * submission.score + COMMENT_WEIGHT * len(list(submission.comments))
        if keyword_count != -1 and weighted_score > MIN_RELEVANT_WEIGHTED_SCORE:
            post_dict = {'title': submission.title, \
            'score': submission.score, \
            'url': submission.url, \
            'comment_count': len(list(submission.comments))}
            matching_posts_info.append((keyword_count, weighted_score, post_dict))
    # Sort asc by the keyword count, then desc by weighted score (can't sort by post_dict)
    matching_posts_info.sort(key=lambda x: (x[0], -1 * x[1]))
    return matching_posts_info

# Send email of matching posts
def send_email():
    matching_posts_info = get_reddit_posts()
    reddit_email_content = ''
    for keyword_count, weighted_score, post in matching_posts_info:
        # Append info for this relevant post to the email content
        reddit_email_content += post['title'] + '<br>' + 'Score: ' + str(post['score']) + \
        '<br>' + 'Comments: ' + str(post['comment_count']) + '<br>' + post['url'] + '<br><br>'
    if len(matching_posts_info) > 0:
        email_list = [
            secrets.RECEIVER_EMAIL
            # Add any other email addresses to send to
        ]
        subject = 'Hey you! I have something SPECIAL for you to check out...'
        # Port 587 is used when sending emails from an app with TLS required
        # See https://support.google.com/a/answer/176600?hl=en
        server = smtplib.SMTP('smtp.gmail.com:587')
        server.ehlo()
        server.starttls()
        server.login(secrets.SENDER_EMAIL, secrets.SENDER_PASSWORD)
        for email_address in email_list:
            # Send emails in multiple part messages
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = secrets.SENDER_EMAIL
            msg['To'] = email_address
            # HTML of email content
            html = '''\
            <html>
              <head></head>
              <body>
                <p>
                    <b style='font-size:20px'>Hello to my favorite person!</b><br><br>
                    I am ecstatic to report that the following posts may be of interest to you:<br>
                </p>
                %s
                <p>
                    <b style='font-size:20px'>With love from your reddit notification script <span style='color:#e06d81'>♥</span></b>
                </p>
              </body>
            </html>
            ''' % reddit_email_content
            msg.attach(MIMEText(html, 'html'))
            server.sendmail(secrets.SENDER_EMAIL, email_address, msg.as_string())
        server.quit()

if __name__ == "__main__":
    send_email()
