import os
from shutil import which
import subprocess
import platform
import argparse
import sys
import json


DEPENDENCIES = ["terraform", "aws"]

profile = ""


def is_dependency_installed(command: str):
    return which(command) is not None


def check_dependencies():
    print("Checking if the dependencies are installed")
    for dep in DEPENDENCIES:
        if is_dependency_installed(dep):
            print(f" - {dep} is installed")
        else:
            print(f"\n{dep} is not installed. Please install it first")
            quit()


def check_aws_session():
    try:
        # Run the AWS CLI command
        result = subprocess.run(
            ['aws', 'sts', 'get-caller-identity'],
            check=True,
            capture_output=True,
            text=True
        )

        # Parse the JSON output
        identity = json.loads(result.stdout)

        print("Active session found:")
        print(f"User ID: {identity['UserId']}")
        print(f"Account: {identity['Account']}")
        print(f"ARN: {identity['Arn']}")
        return True

    except subprocess.CalledProcessError as e:
        print("No active AWS session found or an error occurred.")
        print(f"Error: {e.stderr.strip()}")
        return False

def get_aws_creds():

    profile = input("Please enter your aws-cli profile: ")
    subprocess.run(['aws', 'sso', 'login', '--profile', profile], capture_output=True, text=True)
    
    print("Setting env vars for terraform")
    result = subprocess.run(['aws', 'sts', 'get-session-token'], capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error running aws sts get-session-token: {result.stderr}")
        return None

    # Parse the JSON output
    try:
        credentials = json.loads(result.stdout)['Credentials']
    except json.JSONDecodeError:
        print(f"Error parsing JSON output: {result.stdout}")
        return None
    except KeyError:
        print("Credentials not found in the output")
        return None
 
    os.environ['AWS_PROFILE'] = profile
    os.environ['AWS_ACCESS_KEY_ID'] = credentials['AccessKeyId']
    os.environ['AWS_SECRET_ACCESS_KEY'] = credentials['SecretAccessKey']
    os.environ['AWS_SESSION_TOKEN'] = credentials['SessionToken']
    os.environ['AWS_SESSION_EXPIRATION'] = credentials['Expiration']

def get_terraform_path():
    if os.path.basename(os.getcwd()) == "terraform":
        return "./"
    elif "terraform" in [name for name in os.listdir(".") if os.path.isdir(name)]:
        return "./terraform/"
    else:
        print(
            "\nCan't find the terraform folder. Please change directory into the terraform folder"
        )
        quit()

def is_terraform_apply():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', '-a', dest='is_apply', action='store_true')
    args = parser.parse_args()

    return args.is_apply

def run_terraform():
    print("Please specify which environment / account should be used")
    environment = input("For dev, please just press enter: ") or "dev"

    tf_path = get_terraform_path()
    backend_config = f"{environment}.conf"
    subprocess.run(
        f"(cd {tf_path};terraform init -backend-config={backend_config})",
        shell=True,
        check=True,
    )

    var_file = f"env/{environment}.tfvars"
    
    if is_terraform_apply():
        print('Running terraform apply...')
        subprocess.run(
            f"(cd {tf_path}{command_separator}terraform apply --var-file {var_file})", shell=True
        )
        
    else:
        while True:
            print('Running terraform plan...')
            subprocess.run(
                f"(cd {tf_path}{command_separator}terraform plan --var-file {var_file})", shell=True
            )

            if input("Run terraform plan again? (y/n): ") != 'y':
                quit()

# ---
# Main part
# ---
check_dependencies()
get_aws_creds()
run_terraform()
