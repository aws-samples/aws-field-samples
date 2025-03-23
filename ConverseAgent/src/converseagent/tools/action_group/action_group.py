"""Contains Bedrock Agents action group classes."""

from enum import Enum
from typing import Any, Callable, Dict, List, Literal

from pydantic import BaseModel, Field


class ParentActionGroupSignatureEnum(str, Enum):
    """Represents the parent action group signature for the action group."""

    AMAZON_USER_INPUT = "AMAZON.UserInput"
    AMAZON_CODE_INTERPRETER = "AMAZON.CodeInterpreter"
    ANTHROPIC_COMPUTER = "ANTHROPIC.Computer"
    ANTHROPIC_BASH = "ANTHROPIC.Bash"
    ANTHROPIC_TEXT_EDITOR = "ANTHROPIC.TextEditor"


class ParamTypeEnum(Enum):
    """Represents the parameter type for the action group."""

    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ARRAY = "array"


class Image(BaseModel):
    """Represents an image."""

    file_type: Literal["png", "jpeg", "gif", "webp"] = Field(
        description="The image file_type"
    )
    content_bytes: bytes = Field(description="The image content in bytes")

    def to_boto3_format(self):
        """Format to boto3 request."""
        return {"format": self.file_type, "source": {"bytes": self.content_bytes}}


class ReturnControlActionGroupExecutor(BaseModel):
    """Represents a return of control action group executor.
    
    The Amazon Resource Name (ARN) of the Lambda function containing the business logic \
    that is carried out upon invoking the action or the custom control method for \
    handling the information elicited from the user.
    """

    custom_control: Literal["RETURN_CONTROL"] = Field(
        default="RETURN_CONTROL",
        description="The Amazon Resource Name (ARN) of the Lambda function containing the business logic that \
        is carried out upon invoking the action or the custom control method for \
        handling the information elicited from the user.",
    )

    def to_boto3_format(self):
        """Format to Boto3 request."""
        return {
            "customControl": self.custom_control,
        }


class LambdaActionGroupExecutor(BaseModel):
    """Represents a Lambda action group executor.
    
    The Amazon Resource Name (ARN) of the Lambda function containing the business logic \
    that is carried out upon invoking the action or the custom control method for \
    handling the information elicited from the user.
    """

    lambda_arn: str = Field(
        description="The Amazon Resource Name (ARN) of the Lambda function containing the business logic that \
        is carried out upon invoking the action or the custom control method for \
        handling the information elicited from the user.",
    )

    def to_boto3_format(self):
        """Format to Boto3 request."""
        return {
            "lambda": self.lambda_arn,
        }


class ApiSchema(BaseModel):
    """Represents the OpenAPI schema for the action group."""

    payload: str | None = Field(
        default=None,
        description="The JSON or YAML-formatted payload defining the OpenAPI schema for \
            the action group.",
    )

    s3_bucket_name: str | None = Field(
        default=None,
        description="The name of the S3 bucket where the OpenAPI schema for the action group is stored.",
    )

    s3_object_key: str | None = Field(
        default=None,
        description="The key of the S3 object where the OpenAPI schema for the action group is stored.",
    )

    callable_function: Callable | None = Field(
        default=None,
        description="The callable function for the action group if payload is defined.",
    )

    def model_post_init(self, *args, **kwargs):
        """Validate that only one of payload or s3_bucket_name/s3_object_key pair is provided."""
        has_payload = bool(self.payload)
        has_s3_bucket = bool(self.s3_bucket_name)
        has_s3_key = bool(self.s3_object_key)

        if has_payload and (has_s3_bucket or has_s3_key):
            raise ValueError(
                "Only one of payload or s3_bucket_name and s3_object_key can be provided."
            )

        if not has_payload and not (has_s3_bucket and has_s3_key):
            raise ValueError(
                "Either payload or both s3_bucket_name and s3_object_key must be provided."
            )

    def to_boto3_format(self):
        """Format to Boto3 request."""
        if self.payload:
            return {
                "payload": self.payload,
            }

        if self.s3_bucket_name and self.s3_object_key:
            return {
                "s3": {
                    "s3BucketName": self.s3_bucket_name,
                    "s3ObjectKey": self.s3_object_key,
                }
            }


class FunctionParameter(BaseModel):
    """Represents a function parameter in the action group."""

    name: str = Field(
        description="The name of the function parameter in the action group."
    )

    description: str = Field(
        description="The description of the function parameter in the action group."
    )
    required: bool = Field(
        description="Whether the function parameter is required in the action group."
    )
    param_type: ParamTypeEnum = Field(
        description="The type of the function parameter in the action group."
    )

    def to_boto3_format(self):
        """Format to Boto3 request."""
        return {
            self.name: {
                "description": self.description,
                "required": self.required,
                "type": self.param_type.value,
            }
        }


class Function(BaseModel):
    """Represents a function in the action group."""

    description: str = Field(
        description="The description of the function in the action group."
    )
    name: str = Field(description="The name of the function in the action group.")
    parameters: List[FunctionParameter] = Field(
        default_factory=list,
        description="The parameters of the function in the action group.",
    )
    require_confirmation: bool = Field(
        default=False,
        description="Whether the function requires confirmation in the action group.",
    )

    callable_function: Callable | None = Field(
        default=None,
        description="The callable function for the action group if FunctionSchema is defined.",
    )

    def invoke(self, **kwargs) -> str:
        """Invoke the function."""
        if self.callable_function is None:
            raise ValueError("Callable function is not defined.")

        return str(self.callable_function(**kwargs))

    def to_boto3_format(self) -> Dict[str, Any]:
        """Format to Boto3 request."""
        parameters = {}
        for parameter in self.parameters:
            for k, v in parameter.to_boto3_format().items():
                parameters[k] = v

        return {
            "description": self.description,
            "name": self.name,
            "parameters": parameters,
            "requireConfirmation": "ENABLED"
            if self.require_confirmation
            else "DISABLED",
        }


class FunctionSchema(BaseModel):
    """Represents the function schema for the action group."""

    functions: List[Function] = Field(
        description="The functions in the action group schema."
    )

    def to_boto3_format(self):
        """Format to Boto3 request."""
        return {
            "functions": [function.to_boto3_format() for function in self.functions],
        }


class ActionGroup(BaseModel):
    """Represents a Bedrock Agent action group."""

    name: str = Field(description="The name of the action group.")

    description: str | None = Field(
        default=None, description="The description of the action group."
    )

    executor: ReturnControlActionGroupExecutor | LambdaActionGroupExecutor | None = (
        Field(default=None, description="The action group executor")
    )

    action_group_schema: ApiSchema | FunctionSchema | None = Field(
        default=None, description="The action group schema"
    )

    parent_action_group_signature: ParentActionGroupSignatureEnum | None = Field(
        default=None, description="The parent action group signature"
    )

    parent_action_group_signature_params: Dict[str, str] | None = Field(
        default=None, description="The parent action group signature parameters"
    )

    functions: List[Function] | None = Field(
        default=None, description="The functions in the action group."
    )

    def model_post_init(self, *args, **kwargs):
        """Validate the case for when a parent action group is specified."""
        if self.parent_action_group_signature:
            if self.description or self.action_group_schema or self.executor:
                raise ValueError(
                    "When parent_action_group_signature is specified, description, action_group_schema and executor must not be specified"
                )

    def to_boto3_format(self):
        """Format to Boto3 request."""
        action_group_dict = {
            "actionGroupName": self.name,
        }

        if isinstance(self.action_group_schema, ApiSchema):
            action_group_dict["apiSchema"] = self.action_group_schema.to_boto3_format()
        elif isinstance(self.action_group_schema, FunctionSchema):
            action_group_dict["functionSchema"] = (
                self.action_group_schema.to_boto3_format()
            )

        if self.parent_action_group_signature:
            action_group_dict["parentActionGroupSignature"] = (
                self.parent_action_group_signature
            )

        if self.parent_action_group_signature_params:
            action_group_dict["parentActionGroupSignatureParams"] = (
                self.parent_action_group_signature_params
            )

        if not self.parent_action_group_signature:
            action_group_dict["actionGroupExecutor"] = self.executor.to_boto3_format()
            action_group_dict["description"] = self.description

        return action_group_dict


class FunctionInputParam(BaseModel):
    """Represents the name, type, value inputs of the function invocation input params."""

    name: str = Field(description="The name of the function input param")
    type: str = Field(description="The type of the function input param")
    value: str | int | float | bool = Field(
        description="The value of the function input param"
    )


class InvocationResponseBody(BaseModel):
    """Represents an invocation response body."""

    content_type: Literal["TEXT"] = Field(
        default="TEXT",
        description="The content type of the response body. Currently ony TEXT is supported.",
    )
    body: str = Field(description="The response body")
    images: List[Image] = Field(default_factory=list, description="The images")

    def to_boto3_format(self):
        """Format to boto3 request."""
        response_body_dict = {}

        if self.body:
            response_body_dict[self.content_type] = {"body": self.body}

        if self.images:
            response_body_dict["string"] = {
                "images": [image.to_boto3_format() for image in self.images]
            }

        return response_body_dict


class InvocationResult(BaseModel):
    """Represents an invocation result."""

    action_group: str = Field(description="Name of the action group")
    agent_id: str = Field(description="The agent id")
    confirmation_state: Literal["CONFIRM", "DENY"] | None = Field(
        default=None, description="The confirmation state"
    )
    response_body: InvocationResponseBody = Field(description="The response body")
    response_state: Literal["FAILURE", "REPROMPT"] | None = Field(
        default=None, description="The response state"
    )


class InputParam(BaseModel):
    """Represents a function parameter with type casting capabilities."""

    name: str = Field(description="The name of the function parameter")
    type: ParamTypeEnum = Field(description="The type of the function parameter")
    value: str = Field(description="The raw string value of the function parameter")

    @property
    def cast_value(self) -> str | int | float | bool | list:
        """Cast the string value to the appropriate type based on ParamTypeEnum."""
        try:
            if self.type == ParamTypeEnum.STRING:
                return self.value
            elif self.type == ParamTypeEnum.INTEGER:
                return int(self.value)
            elif self.type == ParamTypeEnum.NUMBER:
                return float(self.value)
            elif self.type == ParamTypeEnum.BOOLEAN:
                return self.value.lower() == "true"
            elif self.type == ParamTypeEnum.ARRAY:
                # Assuming array is provided as comma-separated values
                return [item.strip() for item in self.value.split(",")]
            else:
                return self.value
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"Failed to cast value '{self.value}' to type {self.type}: {str(e)}"
            )

    @classmethod
    def from_dict(cls, param_dict: Dict[str, str]) -> "InputParam":
        """Create a FunctionParam instance from a dictionary with name, type, and value."""
        return cls(
            name=param_dict["name"],
            type=ParamTypeEnum(param_dict["type"].lower()),
            value=param_dict["value"],
        )

    def to_dict(self) -> Dict[str, str]:
        """Convert the FunctionParam instance to a dictionary."""
        return {"name": self.name, "type": self.type.value, "value": self.value}


class FunctionInvocationInput(BaseModel):
    """Represents a function invocation input."""

    action_group_name: str = Field(description="The name of the action group")
    action_invocation_type: Literal[
        "RESULT", "USER_CONFIRMATION", "USER_CONFIRMATION_AND_RESULT"
    ] = Field(description="The action invocation type")
    agent_id: str = Field(description="The agent id")
    collaborator_name: str | None = Field(
        default=None, description="The name of the collaborator if applicable"
    )
    function_name: str = Field(description="The name of the function to call")
    parameters: List[InputParam] = Field(
        default_factory=list,
        description="Function parameter inputs with three inputs: name, type, value",
    )

    @property
    def param_dict(self) -> Dict[str, Any]:
        """Return a dictionary of parameter names and values."""
        return {param.name: param.cast_value for param in self.parameters}


class ApiInvocationInput(BaseModel):
    """Represents an API invocation input."""

    action_group_name: str = Field(description="The name of the action group")
    action_invocation_type: Literal[
        "RESULT", "USER_CONFIRMATION", "USER_CONFIRMATION_AND_RESULT"
    ] = Field(description="The action invocation type")
    agent_id: str = Field(description="The agent id")
    api_path: str = Field(description="The API path")
    http_method: str = Field(description="The HTTP method")
    collaborator_name: str | None = Field(
        default=None, description="The name of the collaborator if applicable"
    )
    parameters: List[InputParam] = Field(
        default_factory=list,
        description="Function parameter inputs with three inputs: name, type, value",
    )

    @property
    def function_name(self) -> str:
        """Return the function name."""
        return self.api_path.split("/")[-1]

    @property
    def param_dict(self) -> Dict[str, Any]:
        """Return a dictionary of parameter names and values."""
        return {param.name: param.cast_value for param in self.parameters}

    def to_event_dict(self) -> Dict[str, Any]:
        """Create event dict."""
        return {
            "agent": self.agent_id,
            "actionGroup": self.action_group_name,
            "function": self.function_name,
            "parameters": [param.to_dict() for param in self.parameters],
        }


class ReturnControlInvocation(BaseModel):
    """Represents a return of control invocation."""

    # action_group_type: Literal["FUNCTION"] = Field(
    #     default="FUNCTION", description="The action group type"
    # )
    invocation_id: str = Field(description="The invocation id")
    invocation_inputs: List[FunctionInvocationInput | ApiInvocationInput] = Field(
        description="A list of function invocation inputs"
    )


class FunctionInvocationResult(InvocationResult):
    """Represents a function invocation result."""

    function_name: str = Field(description="The function name")

    def to_boto3_format(self):
        """Format to boto3 request."""
        return {
            "functionResult": {
                "actionGroup": self.action_group,
                "agentId": self.agent_id,
                "confirmationState": self.confirmation_state,
                "function": self.function_name,
                "responseBody": self.response_body.to_boto3_format(),
                "responseState": self.response_state,
            }
        }


class ApiInvocationResult(InvocationResult):
    """Represents an API invocation result."""

    api_path: str = Field(description="The API path")
    http_method: str = Field(description="The HTTP method")

    def to_boto3_format(self):
        """Format to boto3 request."""
        return {
            "apiResult": {
                "actionGroup": self.action_group,
                "agentId": self.agent_id,
                "apiPath": self.api_path,
                "confirmationState": self.confirmation_state,
                "httpMethod": self.http_method,
                "responseBody": self.response_body.to_boto3_format(),
                "responseState": self.response_state,
            }
        }
