
terraform {
  backend "s3" {
    bucket  = "filesoncloud-terraform-state-7byr6f" # name from bootstrap bucket name output
    key     = "filesoncloud/terraform.state"
    region  = "us-west-2"
    encrypt = true
  }
}
