import textwrap


def custom_html_wraper(text):
    new_string = ""
    for character in text:
        if character != "|":
            new_string += character
        else:
            new_string += "<br>"
    return new_string


def custome_wraper(text):
    new_string = ""
    for character in text:
        if character != "|":
            new_string += character
        else:
            new_string += "\n"
    return new_string