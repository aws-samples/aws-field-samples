import pytest

from converseagent.tools.action_group.action_group import (
    ActionGroup,
    ApiSchema,
    Function,
    FunctionParameter,
    FunctionSchema,
    LambdaActionGroupExecutor,
    ParentActionGroupSignatureEnum,
    ReturnControlActionGroupExecutor,
)


def test_return_control_action_group_executor():
    executor = ReturnControlActionGroupExecutor()

    assert executor.to_boto3_format() == {"customControl": "RETURN_CONTROL"}


def test_lambda_action_group_executor():
    executor = LambdaActionGroupExecutor(lambda_arn="test")

    assert executor.to_boto3_format() == {"lambda": "test"}


class TestOpenApiSchema:
    def test_with_payload(self):
        action_group_schema = ApiSchema(payload="test")

        action_group_schema.to_boto3_format() == {"payload": "test"}

    def test_with_s3(self):
        bucket_name = "bucketA"
        object_key = "keyA"

        action_group_schema = ApiSchema(
            s3_bucket_name=bucket_name, s3_object_key=object_key
        )

        action_group_schema.to_boto3_format() == {
            "s3BucketName": bucket_name,
            "s3ObjectKey": object_key,
        }

    def test_without_payload_and_s3(self):
        # expect to raise error
        with pytest.raises(ValueError):
            ApiSchema()

    def test_with_payload_and_s3(self):
        # expect to raise error
        with pytest.raises(ValueError):
            ApiSchema(payload="test", s3_bucket_name="XXXXXXX", s3_object_key="keyA")

    def test_missing_s3_bucket_name(self):
        # expect to raise error
        with pytest.raises(ValueError):
            ApiSchema(s3_object_key="keyA")

    def test_missing_s3_object_key(self):
        # expect to raise error
        with pytest.raises(ValueError):
            ApiSchema(s3_bucket_name="XXXXXXX")

    def test_format_payload(self):
        action_group_schema = ApiSchema(payload="test")

        assert action_group_schema.to_boto3_format() == {"payload": "test"}

    def test_format_s3(self):
        bucket_name = "XXXXXXX"
        object_key = "keyA"

        action_group_schema = ApiSchema(
            s3_bucket_name=bucket_name, s3_object_key=object_key
        )

        assert action_group_schema.to_boto3_format() == {
            "s3": {
                "s3BucketName": bucket_name,
                "s3ObjectKey": object_key,
            }
        }


def test_function_parameter():
    name = "test"
    description = "test"
    required = False
    param_type = "string"

    function_parameter = FunctionParameter(
        name=name, description=description, required=required, param_type=param_type
    )

    assert function_parameter.to_boto3_format() == {
        name: {
            "description": description,
            "required": required,
            "type": param_type,
        }
    }


def test_function():
    description = "test"
    name = "test"
    parameters = [
        FunctionParameter(
            name="test_param",
            description="test_param",
            required=False,
            param_type="string",
        )
    ]
    require_confirmation = False
    function = Function(
        description=description,
        name=name,
        parameters=parameters,
        require_confirmation=require_confirmation,
    )
    assert function.to_boto3_format() == {
        "description": description,
        "name": name,
        "parameters": {
            "test_param": {
                "description": "test_param",
                "required": False,
                "type": "string",
            }
        },
        "requireConfirmation": "DISABLED",
    }


def test_function_schema():
    functions = [
        Function(
            description="test",
            name="test",
            parameters=[
                FunctionParameter(
                    name="test_param",
                    description="test_param",
                    required=False,
                    param_type="string",
                )
            ],
            require_confirmation=False,
        )
    ]

    function_schema = FunctionSchema(functions=functions)

    assert function_schema.to_boto3_format() == {
        "functions": [
            {
                "description": "test",
                "name": "test",
                "parameters": {
                    "test_param": {
                        "description": "test_param",
                        "required": False,
                        "type": "string",
                    }
                },
                "requireConfirmation": "DISABLED",
            }
        ]
    }


class TestActionGroup:
    name = "test"
    description = "test"

    def test_action_group_with_roc_openapi_schema(self):
        executor = ReturnControlActionGroupExecutor()
        action_group_schema = ApiSchema(payload="test")

        action_group = ActionGroup(
            name=self.name,
            description=self.description,
            executor=executor,
            action_group_schema=action_group_schema,
        )

        assert action_group.to_boto3_format() == {
            "actionGroupExecutor": {"customControl": "RETURN_CONTROL"},
            "actionGroupName": self.name,
            "apiSchema": {"payload": "test"},
            "description": self.description,
        }

    def test_action_group_with_lambda_openapi_schema(self):
        lambda_arn = "arn:test"
        executor = LambdaActionGroupExecutor(lambda_arn=lambda_arn)
        action_group_schema = ApiSchema(payload="test")

        action_group = ActionGroup(
            name=self.name,
            description=self.description,
            executor=executor,
            action_group_schema=action_group_schema,
        )

        assert action_group.to_boto3_format() == {
            "actionGroupExecutor": {"lambda": lambda_arn},
            "actionGroupName": self.name,
            "apiSchema": {"payload": "test"},
            "description": self.description,
        }

    def test_action_group_with_roc_function_schema(self):
        executor = ReturnControlActionGroupExecutor()
        function_schema = FunctionSchema(
            functions=[
                Function(
                    description="test",
                    name="test",
                    parameters=[
                        FunctionParameter(
                            name="test_param",
                            description="test_param",
                            required=False,
                            param_type="string",
                        )
                    ],
                    require_confirmation=False,
                )
            ]
        )

        action_group = ActionGroup(
            name=self.name,
            description=self.description,
            executor=executor,
            action_group_schema=function_schema,
        )

        assert action_group.to_boto3_format() == {
            "actionGroupName": self.name,
            "actionGroupExecutor": {"customControl": "RETURN_CONTROL"},
            "functionSchema": {
                "functions": [
                    {
                        "description": "test",
                        "name": "test",
                        "parameters": {
                            "test_param": {
                                "description": "test_param",
                                "required": False,
                                "type": "string",
                            }
                        },
                        "requireConfirmation": "DISABLED",
                    }
                ]
            },
            "description": self.description,
        }

    def test_action_group_parent_validation(self):
        executor = ReturnControlActionGroupExecutor()
        function_schema = FunctionSchema(
            functions=[
                Function(
                    description="test",
                    name="test",
                    parameters=[
                        FunctionParameter(
                            name="test_param",
                            description="test_param",
                            required=False,
                            param_type="string",
                        )
                    ],
                    require_confirmation=False,
                )
            ]
        )

        parent_action_group_signature = ParentActionGroupSignatureEnum.AMAZON_USER_INPUT

        with pytest.raises(ValueError):
            ActionGroup(
                name=self.name,
                description=self.description,
                executor=executor,
                action_group_schema=function_schema,
                parent_action_group_signature=parent_action_group_signature,
            )

    def test_action_group_parent(self):
        parent_action_group_signature = ParentActionGroupSignatureEnum.AMAZON_USER_INPUT
        parent_action_group_signature_params = {"test": "test"}

        action_group = ActionGroup(
            name=self.name,
            parent_action_group_signature=parent_action_group_signature,
            parent_action_group_signature_params=parent_action_group_signature_params,
        )

        assert action_group.to_boto3_format() == {
            "actionGroupName": self.name,
            "parentActionGroupSignature": "AMAZON.UserInput",
            "parentActionGroupSignatureParams": parent_action_group_signature_params,
        }
