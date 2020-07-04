import http
import logging
from flask import request
from functools import wraps
from exceptions import ValidationException, EntityNotFoundException

# 'http'subclass with set of codes and phrases
successful_codes = [http.HTTPStatus.OK,  # 200
                    http.HTTPStatus.CREATED,  # 201
                    http.HTTPStatus.NO_CONTENT,  # 204
                    http.HTTPStatus.PARTIAL_CONTENT]  # 206

def http_response(http_return_code, msg=None, headers=None):
    if http_return_code not in successful_codes:
        if msg is not None:
            return {'message': msg}, http_return_code
        return {'message': http_return_code.phrase}, http_return_code
    else:
        if msg is not None:
            if headers is not None:
                return msg, http_return_code, headers
            return msg, http_return_code
        else:
            if headers is not None:
                return http_return_code.phrase, http_return_code, headers
            return http_return_code.phrase, http_return_code

#------------------------------------------------------------------------------
def api_exception_handler(func):
    """Default API error codes handling decorator
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)

        except EntityNotFoundException as exc:
            logging.error(exc)  # Report suppression of an error without raising an exception
            return http_response(http.HTTPStatus.NOT_FOUND, str(exc))  # 404

        except ValidationException as exc:
            logging.error(exc)
            return http_response(http.HTTPStatus.BAD_REQUEST, str(exc))  # 400

        except Exception as exc:
            logging.exception(exc)
            return http_response(http.HTTPStatus.INTERNAL_SERVER_ERROR)  # 500

    return wrapper