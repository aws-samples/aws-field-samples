"""Example Lambda for a Bedrock Action Group."""


def lambda_handler(event, context):
    """Add two numbers."""
    print(event)
    agent = event["agent"]
    actionGroup = event["actionGroup"]
    function = event["function"]
    parameters = event.get("parameters", [])
    parameters_dict = {param["name"]: param["value"] for param in parameters}

    x = float(parameters_dict["x"])
    y = float(parameters_dict["y"])
    result = x + y

    responseBody = {"TEXT": {"body": f"{result}"}}

    action_response = {
        "actionGroup": actionGroup,
        "function": function,
        "functionResponse": {"responseBody": responseBody},
    }

    final_response = {
        "response": action_response,
        "messageVersion": event["messageVersion"],
    }
    print("Response: {}".format(final_response))

    return final_response
