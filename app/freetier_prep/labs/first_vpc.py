"""Lab module: "Your first VPC — networks, instances, and secure SSH".

Single source of truth for the launch module:
- base_resources: what the platform provisions (includes one deliberately
  over-permissive firewall rule the student must find and remove)
- tasks: 12 outcome-validated tasks; each has a validator spec (checked by
  validators.py against fake GCP) and a `simulate` spec (the "student did
  the console action" mutation used by the dev UI and E2E tests)
- hcl: the real Terraform artifact template emitted to the student's repo
"""

NET = "ftp-lab-net"
SUBNET = "ftp-lab-subnet"
VM = "ftp-lab-vm"
SSH_TAG = "ssh-target"
BAD_RULE = "ftp-lab-allow-all"
IAP_RANGE = "35.235.240.0/20"

BASE_RESOURCES = [
    {"type": "compute.network", "name": NET,
     "config": {"auto_create_subnetworks": False}},
    {"type": "compute.subnetwork", "name": SUBNET,
     "config": {"network": NET, "cidr": "10.0.1.0/24", "region": "us-central1",
                "private_google_access": False}},
    {"type": "compute.instance", "name": VM,
     "config": {"machine_type": "e2-micro", "network": NET, "subnetwork": SUBNET,
                "tags": [], "labels": {}, "internal_ip": "auto"}},
    # Deliberately over-permissive: task 5/12 teach the student to find & fix it.
    {"type": "compute.firewall", "name": BAD_RULE,
     "config": {"network": NET, "action": "allow", "source_ranges": ["0.0.0.0/0"],
                "ports": ["all"], "target_tags": []}},
]

TASKS = [
    {
        "id": "t01", "title": "Confirm your custom-mode VPC",
        "instructions": "Inspect the provisioned network and confirm it is a "
                        "custom-mode VPC (no auto-created subnets).",
        "validator": {"kind": "config", "resource": NET,
                      "expect": {"auto_create_subnetworks": False},
                      "explain": "The network must be custom-mode: auto-created "
                                 "subnets teach bad habits and waste quota."},
        "simulate": {"noop": True},
    },
    {
        "id": "t02", "title": "Create a second subnet",
        "instructions": "Add subnet ftp-lab-subnet-east 10.0.2.0/24 in us-east1.",
        "validator": {"kind": "config", "resource": "ftp-lab-subnet-east",
                      "expect": {"cidr": "10.0.2.0/24", "region": "us-east1",
                                 "network": NET},
                      "explain": "Need a us-east1 subnet with CIDR 10.0.2.0/24 "
                                 "on the lab network (non-overlapping with 10.0.1.0/24)."},
        "simulate": {"create": {"type": "compute.subnetwork",
                                "name": "ftp-lab-subnet-east",
                                "config": {"network": NET, "cidr": "10.0.2.0/24",
                                           "region": "us-east1",
                                           "private_google_access": False}}},
    },
    {
        "id": "t03", "title": "Tag the VM for SSH targeting",
        "instructions": f"Add network tag '{SSH_TAG}' to the lab VM.",
        "validator": {"kind": "config_contains", "resource": VM,
                      "field": "tags", "value": SSH_TAG,
                      "explain": f"The VM needs the '{SSH_TAG}' network tag so "
                                 "firewall rules can target it without touching "
                                 "other instances."},
        "simulate": {"update": {"resource": VM, "config": {"tags": [SSH_TAG]}}},
    },
    {
        "id": "t04", "title": "Allow SSH via IAP only",
        "instructions": f"Create firewall rule ftp-lab-allow-iap-ssh: allow tcp:22 "
                        f"from {IAP_RANGE} to tag '{SSH_TAG}'.",
        "validator": {"kind": "iap_ssh", "network": NET, "tag": SSH_TAG,
                      "explain": "SSH must be reachable through the IAP tunnel "
                                 f"range {IAP_RANGE}, scoped to the "
                                 f"'{SSH_TAG}' tag — not the whole network."},
        "simulate": {"create": {"type": "compute.firewall",
                                "name": "ftp-lab-allow-iap-ssh",
                                "config": {"network": NET, "action": "allow",
                                           "source_ranges": [IAP_RANGE],
                                           "ports": ["22"],
                                           "target_tags": [SSH_TAG]}}},
    },
    {
        "id": "t05", "title": "Close the internet SSH hole",
        "instructions": "Something in this project still allows SSH from anywhere. "
                        "Find it and fix it (keep the IAP path working).",
        "validator": {"kind": "no_public_ssh", "network": NET, "tag": SSH_TAG,
                      "explain": "A firewall rule still allows tcp:22 from "
                                 "0.0.0.0/0. External SSH must be blocked while "
                                 "IAP-tunneled SSH keeps working."},
        "simulate": {"delete": {"resource": BAD_RULE}},
    },
    {
        "id": "t06", "title": "Enable Private Google Access",
        "instructions": "Turn on Private Google Access for the primary subnet so "
                        "instances without external IPs can reach Google APIs.",
        "validator": {"kind": "config", "resource": SUBNET,
                      "expect": {"private_google_access": True},
                      "explain": "Private Google Access must be enabled on "
                                 f"{SUBNET}."},
        "simulate": {"update": {"resource": SUBNET,
                                "config": {"private_google_access": True}}},
    },
    {
        "id": "t07", "title": "Create a uniform-access bucket",
        "instructions": "Create bucket ftp-lab-assets with uniform bucket-level "
                        "access enabled.",
        "validator": {"kind": "config", "resource": "ftp-lab-assets",
                      "expect": {"uniform_access": True},
                      "explain": "The bucket must exist with uniform bucket-level "
                                 "access (per-object ACLs are a legacy footgun)."},
        "simulate": {"create": {"type": "storage.bucket", "name": "ftp-lab-assets",
                                "config": {"uniform_access": True,
                                           "location": "US"}}},
    },
    {
        "id": "t08", "title": "Grant least-privilege viewer access",
        "instructions": "Grant serviceAccount:auditor@lab.dev the "
                        "roles/compute.viewer role — and nothing broader.",
        "validator": {"kind": "iam_least_priv", "member": "auditor@lab.dev",
                      "required": "roles/compute.viewer",
                      "forbidden": ["roles/editor", "roles/owner"],
                      "explain": "auditor@lab.dev needs roles/compute.viewer "
                                 "exactly. Editor/owner grants fail the "
                                 "least-privilege requirement."},
        "simulate": {"iam": {"member": "auditor@lab.dev",
                             "role": "roles/compute.viewer"}},
    },
    {
        "id": "t09", "title": "Verify IAP SSH path end-to-end",
        "instructions": "Confirm the VM is reachable over SSH through IAP and "
                        "not from the public internet.",
        "validator": {"kind": "iap_only_ssh", "network": NET, "tag": SSH_TAG,
                      "explain": "Reachability must be: IAP tunnel → yes, "
                                 "public internet → no. Both conditions checked."},
        "simulate": {"noop": True},
    },
    {
        "id": "t10", "title": "Label the VM",
        "instructions": "Add label env=lab to the VM for cost attribution.",
        "validator": {"kind": "config_label", "resource": VM,
                      "label": "env", "value": "lab",
                      "explain": "The VM needs the env=lab label — unlabeled "
                                 "resources make billing attribution impossible."},
        "simulate": {"update_label": {"resource": VM, "label": "env",
                                      "value": "lab"}},
    },
    {
        "id": "t11", "title": "Reserve a static internal IP",
        "instructions": "Reserve internal address ftp-lab-ip = 10.0.1.10 and "
                        "assign it to the VM.",
        "validator": {"kind": "static_ip", "address_name": "ftp-lab-ip",
                      "ip": "10.0.1.10", "vm": VM,
                      "explain": "Address ftp-lab-ip must reserve 10.0.1.10 and "
                                 "the VM must use it (internal_ip=10.0.1.10)."},
        "simulate": {"static_ip": {"address_name": "ftp-lab-ip",
                                   "ip": "10.0.1.10", "vm": VM,
                                   "subnet": SUBNET}},
    },
    {
        "id": "t12", "title": "Prove the cleanup habit",
        "instructions": "The over-permissive rule from earlier should be gone, and "
                        "no other allow-all rule may exist on the lab network.",
        "validator": {"kind": "no_allow_all", "network": NET,
                      "explain": "No firewall rule on the lab network may allow "
                                 "all ports from 0.0.0.0/0."},
        "simulate": {"noop": True},
    },
]

HCL = """terraform {
  required_providers {
    google = { source = "hashicorp/google", version = "~> 6.0" }
  }
}

resource "google_compute_network" "lab" {
  name                    = "ftp-lab-net"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "lab" {
  name                     = "ftp-lab-subnet"
  network                  = google_compute_network.lab.id
  ip_cidr_range            = "10.0.1.0/24"
  region                   = "us-central1"
  private_ip_google_access = true
}

resource "google_compute_subnetwork" "lab_east" {
  name          = "ftp-lab-subnet-east"
  network       = google_compute_network.lab.id
  ip_cidr_range = "10.0.2.0/24"
  region        = "us-east1"
}

resource "google_compute_firewall" "allow_iap_ssh" {
  name          = "ftp-lab-allow-iap-ssh"
  network       = google_compute_network.lab.id
  source_ranges = ["35.235.240.0/20"]
  target_tags   = ["ssh-target"]
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
}

resource "google_compute_address" "lab_internal" {
  name         = "ftp-lab-ip"
  address_type = "INTERNAL"
  address      = "10.0.1.10"
  subnetwork   = google_compute_subnetwork.lab.id
  region       = "us-central1"
}

resource "google_compute_instance" "lab" {
  name         = "ftp-lab-vm"
  machine_type = "e2-micro"
  zone         = "us-central1-a"
  tags         = ["ssh-target"]
  labels       = { env = "lab" }
  boot_disk {
    initialize_params { image = "debian-cloud/debian-12" }
  }
  network_interface {
    subnetwork = google_compute_subnetwork.lab.id
    network_ip = google_compute_address.lab_internal.address
  }
}

resource "google_storage_bucket" "assets" {
  name                        = "ftp-lab-assets"
  location                    = "US"
  uniform_bucket_level_access = true
}
"""

LAB = {
    "id": "first-vpc",
    "title": "Your first VPC — networks, instances, and secure SSH",
    "credit_estimate_usd": 0.0,
    "required_policies": ["constraints/iam.disableWorkloadIdentityFederation"],
    "quota_needed": {"e2-micro": 1},
    "base_resources": BASE_RESOURCES,
    "tasks": TASKS,
    "hcl": HCL,
}
