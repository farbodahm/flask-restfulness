from itsdangerous import (TimedJSONWebSignatureSerializer
                          as Serializer, BadSignature, SignatureExpired)
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, FileSystemLoader

from src.DbHandler import DbHandler

import secrets
import string
import json
import smtplib
from typing import Text

# Load config file to read Serializer secret key
with open('config.json', mode='r') as config_file:
    CONFIG = json.load(config_file)

SECRET_KEY = CONFIG.get('forget_password', {}).get('serializer_secret_key')


class ResetPasswordCore:
    """Core Functions of reseting user's password."""
    @staticmethod
    def get_n_digit_auth_code(username: str) -> str:
        """ Step 1: Start process of resetting password. Return hash format of
        user's ID + random generated N digit code."""
        id = DbHandler.get_user_id(username)
        if id == -1:
            return "USER_NOT_FOUND"

        random_code = ResetPasswordCore.__generate_n_digit_code()
        forget_password_rendered_page = ResetPasswordCore.\
            __render_forget_password_page(random_code)

        ResetPasswordCore.__send_email_to_user(
            username,
            'Restfulness Forget Password Code',
            forget_password_rendered_page)

        return(ResetPasswordCore.__generate_hash_string(id, random_code))

    @staticmethod
    def get_password_reset_token(hashed_data: str, user_input: str) -> str:
        """ Step 2: Return token for reseting password if user inputed correct
        N digit code."""
        try:
            user_id = ResetPasswordCore.__verify_user_input_with_hashed_data(
                hashed_data, user_input)
        except SignatureExpired:
            return('EXPIRED')
        except BadSignature:
            return('INVALID_TOKEN')

        if user_id == -1:
            return('INVALID_CODE')
        else:
            return(ResetPasswordCore.__generate_reset_password_token(user_id))

    @staticmethod
    def reset_password(reset_token: str, new_password: str) -> str:
        """ Step 3: Change user's password if the token for changing
        password is valid"""
        try:
            user_id = ResetPasswordCore.__validate_reset_password_token(
                reset_token)
        except SignatureExpired:
            return('EXPIRED')
        except BadSignature:
            return('INVALID_TOKEN')

        status = DbHandler.reset_user_forgotten_password(user_id, new_password)
        if status == 'OK':
            return('OK')
        else:
            return('FAILED')

    @staticmethod
    def __validate_reset_password_token(token: str) -> int:
        """ Return user's ID if reset password token is correct. """
        hash = Serializer(SECRET_KEY)
        try:
            data = hash.loads(token)
        except SignatureExpired:
            raise
        except BadSignature:
            raise

        return(data['id'])

    @staticmethod
    def __verify_user_input_with_hashed_data(hashed_data: str,
                                             user_input: str) -> int:
        """ Verify if user's inputed N digit code is correct, if so,
        return users id."""
        hash = Serializer(SECRET_KEY)
        try:
            data = hash.loads(hashed_data)
        except SignatureExpired:
            raise
        except BadSignature:
            raise

        if user_input == data['valid_code']:
            return(data['id'])
        else:
            return(-1)

    @staticmethod
    def __generate_reset_password_token(id: int) -> str:
        """ Generate the main token that reset user's password."""
        expire_time = CONFIG.get('forget_password', {}).\
            get('reset_password_token_expire_seconds')

        hash = Serializer(SECRET_KEY, expires_in=expire_time)
        return(
            str(
                hash.dumps({
                    'id': id
                }),
                'utf-8'
            )
        )

    @staticmethod
    def __generate_hash_string(id: int, random_code: str) -> str:
        """ Create a hash that contains (user's ID and valid
        random created N digit code) which expires in seconds read
        from config file. """
        expire_time = CONFIG.get('forget_password', {}).\
            get('validation_token_expire_seconds')

        hash = Serializer(SECRET_KEY, expires_in=expire_time)
        return(
            str(
                hash.dumps({
                    'id': id,
                    'valid_code': random_code
                }),
                'utf-8'
            )
        )

    @staticmethod
    def __send_email_to_user(username: str, subject: str, msg_body: Text):
        """ Send Email to username's Email. msg_body is Jinja2
        rendered template."""
        host = CONFIG.get('smtp', {}).get('host')
        port = CONFIG.get('smtp', {}).get('port')
        sender_email = CONFIG.get('smtp', {}).get('server_username')
        password = CONFIG.get('smtp', {}).get('server_password')

        # For passing CI tests
        if host == 'your_host_address_here':
            return

        smtp_server = smtplib.SMTP(host=host, port=port)
        smtp_server.starttls()
        smtp_server.login(sender_email, password)

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = username
        msg['Subject'] = subject
        body_rendered = msg_body
        msg.attach(MIMEText(body_rendered, 'html'))

        smtp_server.send_message(msg)
        smtp_server.quit()

    @staticmethod
    def __generate_n_digit_code() -> str:
        """ For generating random N digit of integers."""
        code_length = CONFIG.get('forget_password', {}).\
            get('reset_password_code_length')

        result_str = ''.join(
            secrets.choice(string.digits) for i in range(code_length)
        )
        return result_str

    @staticmethod
    def __render_forget_password_page(random_code: str) -> Text:
        """ Using Jinja2 to render forget password email page. """
        env = Environment(loader=FileSystemLoader('templates/'),
                          autoescape=True)
        template = env.get_template('forget_password.html')
        return(template.render(code=random_code))
