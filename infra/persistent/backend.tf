terraform {
  backend "s3" {
    bucket  = "filesoncloud-terraform-state-7byr6f"
    key     = "filesoncloud/persistent.tfstate"
    region  = "us-west-2"
    encrypt = true
  }
}
