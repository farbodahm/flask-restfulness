from common.DbHandler import DbHandler

from itsdangerous import (TimedJSONWebSignatureSerializer
                          as Serializer, BadSignature, SignatureExpired)

import random
import string


class ResetPasswordCore:
    """Core Functions of reseting user's password."""
    @staticmethod
    def get_8_digit_auth_code(username: str) -> str:
        id = DbHandler.get_user_id(username)
        if id is None:
            return "USER_NOT_FOUND"

        random_code = ResetPasswordCore.__generate_8_digit_code()
        ResetPasswordCore.__send_8_digit_code_to_users_email(
            username, random_code)

        return(
            ResetPasswordCore.__generate_hash_string(id, random_code)
        )

    @staticmethod
    def __generate_hash_string(id: int, random_code: str) -> str:
        """ Create a hash that contains (user's ID and valid
        random created 8 digit code) which expires in 300 seconds."""
        hash = Serializer('test', expires_in=300)
        return(
            hash.dumps({
                'id': id,
                'valid_code': random_code
            })
        )

    @staticmethod
    def __send_8_digit_code_to_users_email(username: str, random_code: str):
        """ Send random generated password to user's email."""
        # TODO: Implement sending email part
        pass

    @staticmethod
    def __generate_8_digit_code() -> str:
        """ For generating random 8 digit of integers."""
        result_str = ''.join(
            random.choice(string.digits) for i in range(8)
        )
        return result_str
