Subagent: 10af52b8-02f0-4cba-bd7c-fd2ef10a131c

## Complete Compartment Hierarchy (76 compartments)

### Root Level (tamam tenancy)

```
tamam (tenancy)
├── garbage-collector
│   ├── oci-poc-comp
│   │   └── poc-compute
│   ├── Stagging_Environment
│   │   └── N_S-Compartment
│   └── UAT_Environment
│       ├── CISLZSTG-appdev-cmp
│       ├── CISLZSTG-database-cmp
│       ├── CISLZSTG-network-cmp
│       └── CISLZSTG-security-cmp
│
├── ManagedCompartmentForPaaS
│
├── tamam-production-env ⭐
│   ├── prd-erp
│   │   ├── prd-erp-compute
│   │   └── prd-erp-networking
│   ├── prod-ad1
│   │   ├── prod-ad1-compute
│   │   └── prod-ad1-networking
│   ├── prod-audit
│   │   ├── prod-audit-compute
│   │   └── prod-audit-networking
│   ├── prod-benchmatrix
│   │   ├── prod-benchmatrix-compute
│   │   └── prod-benchmatrix-networking
│   ├── prod-born-interactive
│   │   ├── prod-interactive-compute
│   │   └── prod-interactive-networking
│   ├── prod-dmz
│   │   ├── prod-dmz-compute
│   │   └── prod-dmz-networking
│   ├── prod-foo
│   │   ├── prod-foo-compute
│   │   └── prod-foo-networking
│   ├── prod-hub
│   │   ├── prod-hub-compute
│   │   ├── prod-hub-networking
│   │   └── Prod-int-ltm
│   ├── prod-intellect
│   │   ├── prod-intellect-compute
│   │   └── prod-intellect-networking
│   ├── prod-kepler
│   │   ├── prod-kepler-compute
│   │   └── prod-kepler-networking
│   ├── prod-optasia
│   │   ├── prod-optasia-compute
│   │   └── prod-optasia-networking
│   ├── prod-tamam
│   │   ├── prod-tamam-compute
│   │   └── prod-tamam-networking
│   └── prod-tamam-cyber
│       ├── prod-cyber-compute
│       └── prod-cyber-networking
│
├── tamam-staging-env
│   ├── staging-ad1
│   │   ├── staging-ad1-compute
│   │   └── staging-ad1-networking
│   ├── staging-benchmatrix
│   │   ├── staging-benchmatrix-compute
│   │   └── staging-benchmatrix-networking
│   ├── staging-cyber
│   │   ├── staging-cyber-compute
│   │   └── staging-cyber-networking
│   ├── staging-dmz
│   │   ├── staging-dmz-compute
│   │   └── staging-dmz-networking
│   ├── staging-erp
│   │   ├── staging-erp-compute
│   │   └── staging-erp-networking
│   ├── staging-foo
│   │   ├── staging-foo-compute
│   │   └── staging-foo-networking
│   ├── staging-hub
│   │   ├── staging-hub-compute
│   │   ├── staging-hub-networking
│   │   └── staging-sec-int-ltm
│   ├── staging-intellect
│   │   ├── staging-intellect-compute
│   │   └── staging-intellect-networking
│   ├── staging-interactive
│   │   ├── staging-interactive-compute
│   │   └── staging-interactive-networking
│   ├── staging-kepler
│   │   ├── staging-kepler-compute
│   │   └── staging-kepler-networking
│   ├── staging-monitor
│   ├── staging-optasia
│   │   ├── staging-optasia-compute
│   │   └── staging-optasia-networking
│   ├── staging-tamam
│   │   ├── staging-tamam-compute
│   │   └── staging-tamam-networking
│   └── stagging-testing
│       ├── testing-compute
│       └── testing-networking
│
└── tamam-universal-resources
```

The structure follows a consistent pattern with **compute** and **networking** sub-compartments for each workload (tamam, intellect, kepler, optasia, benchmatrix, foo, etc.) across both production and staging environments.

USER:
i want list of all compartment and child compartment 

AGENT:

**Command Executed:**

```bash
C:\Users\hosam\bin\oci.exe iam compartment list --compartment-id ocid1.tenancy.oc1..aaaaaaaawotzr2kkpzydktoyolhcgyahaefl4pgec73lkghvmhbphdmhuszq --compartment-id-in-subtree true --all
```

**Output:**

```
Warning: To increase security of your API key located at C:\Users\hosam\.oci\oci_api_key.pem, append an extra line with 'OCI_API_KEY' at the end. For more information, refer to https://docs.oracle.com/iaas/Content/API/Concepts/apisigningkey.htm. To suppress the warning, set the env variable SUPPRESS_LABEL_WARNING=True
{
  "data": [
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaakq7ypj7hvxhvhchcax5eq66oos47nlumkyclmslr3psif3d7uliq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/ahmad.almamo@tamam.life",
          "CreatedOn": "2023-11-26T13:44:01.648Z"
        }
      },
      "description": "CIS Landing Zone compartment for all resources related to application development: compute instances, storage, functions, OKE, API Gateway, streaming, and others.",
      "freeform-tags": {
        "cis-landing-zone": "CISLZSTG-quickstart/2.6.5\n",
        "cislz-terraform-module": "iam-compartments/0.1.6\n"
      },
      "id": "ocid1.compartment.oc1..aaaaaaaakojkzxzy6ie6ltj4pftujvpkwmjl2b63qddc4u55iwontut3huxq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "CISLZSTG-appdev-cmp",
      "time-created": "2023-11-26T13:44:02.456000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaakq7ypj7hvxhvhchcax5eq66oos47nlumkyclmslr3psif3d7uliq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/ahmad.almamo@tamam.life",
          "CreatedOn": "2023-11-26T13:44:01.797Z"
        }
      },
      "description": "CIS Landing Zone compartment for all database related resources.",
      "freeform-tags": {
        "cis-landing-zone": "CISLZSTG-quickstart/2.6.5\n",
        "cislz-terraform-module": "iam-compartments/0.1.6\n"
      },
      "id": "ocid1.compartment.oc1..aaaaaaaanpyro6gh2xnl2ly7iwfv2swgru5z77k7acqyfvwcabifwkx7zbjq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "CISLZSTG-database-cmp",
      "time-created": "2023-11-26T13:44:02.147000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaakq7ypj7hvxhvhchcax5eq66oos47nlumkyclmslr3psif3d7uliq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/ahmad.almamo@tamam.life",
          "CreatedOn": "2023-11-26T13:44:01.698Z"
        }
      },
      "description": "CIS Landing Zone compartment for all network related resources: VCNs, subnets, network gateways, security lists, NSGs, load balancers, VNICs, and others.",
      "freeform-tags": {
        "cis-landing-zone": "CISLZSTG-quickstart/2.6.5\n",
        "cislz-terraform-module": "iam-compartments/0.1.6\n"
      },
      "id": "ocid1.compartment.oc1..aaaaaaaaxmmq7er5k564ieyszj6zer7keediu4ftqed5b3c67nlami5aajqa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "CISLZSTG-network-cmp",
      "time-created": "2023-11-26T13:44:01.952000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaakq7ypj7hvxhvhchcax5eq66oos47nlumkyclmslr3psif3d7uliq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/ahmad.almamo@tamam.life",
          "CreatedOn": "2023-11-26T13:44:01.690Z"
        }
      },
      "description": "CIS Landing Zone compartment for all security related resources: vaults, topics, notifications, logging, scanning, and others.",
      "freeform-tags": {
        "cis-landing-zone": "CISLZSTG-quickstart/2.6.5\n",
        "cislz-terraform-module": "iam-compartments/0.1.6\n"
      },
      "id": "ocid1.compartment.oc1..aaaaaaaa3v7s2gvjc4yfotbcmttngspxaf3gtabbm6vkhuuusuvegvhdck3q",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "CISLZSTG-security-cmp",
      "time-created": "2023-11-26T13:44:01.735000+00:00"
    },
    {
      "compartment-id": "ocid1.tenancy.oc1..aaaaaaaawotzr2kkpzydktoyolhcgyahaefl4pgec73lkghvmhbphdmhuszq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-07-26T10:49:53.259Z"
        }
      },
      "description": "garbage-collector",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaaplwesz6cs5qdh3qkecasdphs3dojfe3k2rz6fef6boaps4hgghpa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "garbage-collector",
      "time-created": "2024-07-26T10:49:53.488000+00:00"
    },
    {
      "compartment-id": "ocid1.tenancy.oc1..aaaaaaaawotzr2kkpzydktoyolhcgyahaefl4pgec73lkghvmhbphdmhuszq",
      "defined-tags": {},
      "description": "idcs-912bbbb800f7442691c18b5e865c8794|27839004|شركة الاتصالات المتنقلة السعودية",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaay4qtumhpeeiibf3zlbdjqbmhxn2v46klqbvmkghf7mglzxwrii6a",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "ManagedCompartmentForPaaS",
      "time-created": "2023-11-07T09:17:31.269000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaad6xkhrs3fi7j7d5yrof32bp72jt434dzpvcor22dbqj7grpz5kpa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/mutaz.modawy@tamam.life",
          "CreatedOn": "2024-05-17T12:41:41.596Z"
        }
      },
      "description": "Network & Security Compartment",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaadhtfdp545hcia52wep5s7komm2yuivppg3crapd4n6qomqwmi3zq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "N_S-Compartment",
      "time-created": "2024-05-17T12:41:41.708000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaaplwesz6cs5qdh3qkecasdphs3dojfe3k2rz6fef6boaps4hgghpa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-08T01:37:51.235Z"
        }
      },
      "description": "a compartment dedicated for testing concepts and ensuring applicability",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa5qbtywhcuvuqhnecr2cjt3etvgviy6nrsi4nmozl4lt5kd7ndhjq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "oci-poc-comp",
      "time-created": "2024-05-08T01:37:51.293000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa5qbtywhcuvuqhnecr2cjt3etvgviy6nrsi4nmozl4lt5kd7ndhjq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-08T01:39:27.813Z"
        }
      },
      "description": "Compute resources",
      "freeform-tags": {
        "enviroment": "poc"
      },
      "id": "ocid1.compartment.oc1..aaaaaaaaxs64npqx56thybfgmh37nfg4lugn7hdrb7mfby6qwtzz4ien67eq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "poc-compute",
      "time-created": "2024-05-08T01:39:27.863000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa4lgys6g3puvk3icrap7rmfaxa6mggqxbigoolxvd3sr2ci4tn2oq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2025-01-15T11:15:19.513Z"
        }
      },
      "description": "prd-erp",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaafqtqvjw4bttatghqux2aknnf6fmjyuvqg2jarxmeyieyucqigi7a",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prd-erp",
      "time-created": "2025-01-15T11:15:19.565000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaafqtqvjw4bttatghqux2aknnf6fmjyuvqg2jarxmeyieyucqigi7a",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2025-01-15T11:16:27.661Z"
        }
      },
      "description": "prd-erp-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaaohetdfg6rddm3s6wahdv7xzsovbwpkzx4p2nynrmyjtxvwuvhusq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prd-erp-compute",
      "time-created": "2025-01-15T11:16:27.719000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaafqtqvjw4bttatghqux2aknnf6fmjyuvqg2jarxmeyieyucqigi7a",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2025-01-15T11:16:33.823Z"
        }
      },
      "description": "prd-erp-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaatpm2nzpfhpftlayljcw3ixw6wjv5p4eosz6uqksj6j7biqqnjgna",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prd-erp-networking",
      "time-created": "2025-01-15T11:16:33.841000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa4lgys6g3puvk3icrap7rmfaxa6mggqxbigoolxvd3sr2ci4tn2oq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:55:35.969Z"
        }
      },
      "description": "prod-ad1",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaas67uiukraavgczkz2hyaab3gm7p37pp3pujlhdtecu5x4x24ifja",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-ad1",
      "time-created": "2024-08-02T04:55:35.997000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaas67uiukraavgczkz2hyaab3gm7p37pp3pujlhdtecu5x4x24ifja",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:57:06.642Z"
        }
      },
      "description": "prod-ad1-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa3qcqb2sisa6e7yh3mt3flersxe5k6nc2ajlkunkasktynnsstkpa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-ad1-compute",
      "time-created": "2024-08-02T04:57:06.707000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaas67uiukraavgczkz2hyaab3gm7p37pp3pujlhdtecu5x4x24ifja",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:57:16.016Z"
        }
      },
      "description": "prod-ad1-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaak7tubztngmsneexgtmfvpd7wo7xcsnu22o6dh3dv2yqgs76gjryq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-ad1-networking",
      "time-created": "2024-08-02T04:57:16.077000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa4lgys6g3puvk3icrap7rmfaxa6mggqxbigoolxvd3sr2ci4tn2oq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/mutaz.modawy@tamam.life",
          "CreatedOn": "2025-07-31T07:51:32.663Z"
        }
      },
      "description": "prod-audit",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaag2va3um3vf7lcorgxsiucnewnbzjrdt6aelra5kpu45kghtel7xa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-audit",
      "time-created": "2025-07-31T07:51:33.001000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaag2va3um3vf7lcorgxsiucnewnbzjrdt6aelra5kpu45kghtel7xa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/mutaz.modawy@tamam.life",
          "CreatedOn": "2025-07-31T07:54:44.108Z"
        }
      },
      "description": "prod-audit-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaakdesfr2hizxein44p6ohbc4kzalxijeicqudpv4qlv4ezkqm6mbq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-audit-compute",
      "time-created": "2025-07-31T07:54:44.152000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaag2va3um3vf7lcorgxsiucnewnbzjrdt6aelra5kpu45kghtel7xa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/mutaz.modawy@tamam.life",
          "CreatedOn": "2025-07-31T07:55:42.391Z"
        }
      },
      "description": "prod-audit-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaaearqlf2pmjqxcaqbqubcgn772ebyghki6s2mjvohe5mc556rtojq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-audit-networking",
      "time-created": "2025-07-31T07:55:42.478000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa4lgys6g3puvk3icrap7rmfaxa6mggqxbigoolxvd3sr2ci4tn2oq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:55:45.889Z"
        }
      },
      "description": "prod-benchmatrix",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaafp7d5mecyqwnt6vucswmqa5qvm77heggfhsjccs23g2v6nhgi5xq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-benchmatrix",
      "time-created": "2024-08-02T04:55:45.918000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaafp7d5mecyqwnt6vucswmqa5qvm77heggfhsjccs23g2v6nhgi5xq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:57:45.106Z"
        }
      },
      "description": "prod-benchmatrix-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaax5cz2espy4fxpjeaxkwdehy4rh4vgwwxqr6hwlfhgfilpmfz4dyq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-benchmatrix-compute",
      "time-created": "2024-08-02T04:57:45.154000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaafp7d5mecyqwnt6vucswmqa5qvm77heggfhsjccs23g2v6nhgi5xq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:57:58.036Z"
        }
      },
      "description": "prod-benchmatrix-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaacd3sqxcqlusceejueklmp7djit4bycw23gd7pjk7b6mka4zy75yq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-benchmatrix-networking",
      "time-created": "2024-08-02T04:57:58.078000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa4lgys6g3puvk3icrap7rmfaxa6mggqxbigoolxvd3sr2ci4tn2oq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-12-23T15:55:10.311Z"
        }
      },
      "description": "website compartment",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaanyn5qbo4xvd6qoyhfy3jkf7mthohgjuemttemxojtkacrli2kqda",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-born-interactive",
      "time-created": "2024-12-23T15:55:10.377000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanoberqzqqbsmn4q5bligpjeyfvbls3tagysbdidxvxfvsbht63jq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-10-21T11:57:38.914Z"
        }
      },
      "description": "prod-cyber-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaaingfoprklhejxgmi4iioqnon2k5zq32theto545zmfoujzrcodoa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-cyber-compute",
      "time-created": "2024-10-21T11:57:38.968000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanoberqzqqbsmn4q5bligpjeyfvbls3tagysbdidxvxfvsbht63jq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-10-21T11:57:52.912Z"
        }
      },
      "description": "prod-cyber-network",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaaugwikr4obsajq2afls57ilbdja7k54h2353id7ens5acodftntha",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-cyber-networking",
      "time-created": "2024-10-21T11:57:52.943000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa4lgys6g3puvk3icrap7rmfaxa6mggqxbigoolxvd3sr2ci4tn2oq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/mutaz.modawy@tamam.life",
          "CreatedOn": "2024-08-03T11:57:24.380Z"
        }
      },
      "description": "prod-dmz",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaar5ybm7jbocn4ili7mv2nnd2aarcniwk57h3w5vo4vfec57thx32q",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-dmz",
      "time-created": "2024-08-03T11:57:24.455000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaar5ybm7jbocn4ili7mv2nnd2aarcniwk57h3w5vo4vfec57thx32q",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/mutaz.modawy@tamam.life",
          "CreatedOn": "2024-08-03T11:58:09.573Z"
        }
      },
      "description": "prod-dmz-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaarypqho6ibtwcdqj57ldnofbjzz544augsn7ytjzphrn2z5hopm5q",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-dmz-compute",
      "time-created": "2024-08-03T11:58:09.640000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaar5ybm7jbocn4ili7mv2nnd2aarcniwk57h3w5vo4vfec57thx32q",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/mutaz.modawy@tamam.life",
          "CreatedOn": "2024-08-03T11:58:41.778Z"
        }
      },
      "description": "prod-dmz-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaammdxtn6pflccmfhz64e5rnnjq6lxt4vwkgwabmx3ikhbhprv5jta",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-dmz-networking",
      "time-created": "2024-08-03T11:58:41.827000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa4lgys6g3puvk3icrap7rmfaxa6mggqxbigoolxvd3sr2ci4tn2oq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:55:25.596Z"
        }
      },
      "description": "prod-foo",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaanedvgdyty2nkc2m7du6hceenua6bvytzoj4rv2majl3l5wg54ccq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-foo",
      "time-created": "2024-08-02T04:55:25.651000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanedvgdyty2nkc2m7du6hceenua6bvytzoj4rv2majl3l5wg54ccq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:57:26.574Z"
        }
      },
      "description": "prod-foo-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaatws2kz5otltejzfzn5geepibc5y5wpfxhgmg3abgsp2n3rh77iwq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-foo-compute",
      "time-created": "2024-08-02T04:57:26.618000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanedvgdyty2nkc2m7du6hceenua6bvytzoj4rv2majl3l5wg54ccq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:57:34.228Z"
        }
      },
      "description": "prod-foo-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa34lirjyaya7qboejhwzg3jog54mhgcgmh3hgybigsixxtirctq6q",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-foo-networking",
      "time-created": "2024-08-02T04:57:34.262000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa4lgys6g3puvk3icrap7rmfaxa6mggqxbigoolxvd3sr2ci4tn2oq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:56:24.297Z"
        }
      },
      "description": "prod-hub",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaap7d6vntdn3mvbq63gucgn3kh6uf3bwpysxtfpdql7yhdkhujmzka",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-hub",
      "time-created": "2024-08-02T04:56:24.316000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaap7d6vntdn3mvbq63gucgn3kh6uf3bwpysxtfpdql7yhdkhujmzka",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:58:12.013Z"
        }
      },
      "description": "prod-hub-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa2f4qa43tuokkleuakvoirbyhqkthrkm5b6vkabdxefuo66tdjdpq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-hub-compute",
      "time-created": "2024-08-02T04:58:12.052000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaap7d6vntdn3mvbq63gucgn3kh6uf3bwpysxtfpdql7yhdkhujmzka",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:58:20.890Z"
        }
      },
      "description": "prod-hub-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaagchbum3mvn663b6mj5uf4rdni7qloaciinko7fgwl6sorskeqriq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-hub-networking",
      "time-created": "2024-08-02T04:58:20.921000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaap7d6vntdn3mvbq63gucgn3kh6uf3bwpysxtfpdql7yhdkhujmzka",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/mutaz.modawy@tamam.life",
          "CreatedOn": "2024-10-03T12:28:36.854Z"
        }
      },
      "description": "Prod-int-ltm",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa4oseiku73gyj6wxwlrxgszn3vfwq6x3nxnj3y5nktr5uksysacbq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "Prod-int-ltm",
      "time-created": "2024-10-03T12:28:36.914000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa4lgys6g3puvk3icrap7rmfaxa6mggqxbigoolxvd3sr2ci4tn2oq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:56:03.566Z"
        }
      },
      "description": "prod-intellect",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaaaq3tjewk6btvq4ke6dtydphyuzwtvdo455x47y4j6hq45vovvjmq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-intellect",
      "time-created": "2024-08-02T04:56:03.623000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaaaq3tjewk6btvq4ke6dtydphyuzwtvdo455x47y4j6hq45vovvjmq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:58:33.069Z"
        }
      },
      "description": "prod-intellect-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaas4zz2bcg3bhhs2b2haefg4n7iapv7dab7pvne4fhr4uakjqvwx7q",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-intellect-compute",
      "time-created": "2024-08-02T04:58:33.101000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaaaq3tjewk6btvq4ke6dtydphyuzwtvdo455x47y4j6hq45vovvjmq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:58:41.393Z"
        }
      },
      "description": "prod-intellect-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa7utvgyuhtn6afrdtoqqcvwogjgihzp5x5orwwccslx5hpum4golq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-intellect-networking",
      "time-created": "2024-08-02T04:58:41.452000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanyn5qbo4xvd6qoyhfy3jkf7mthohgjuemttemxojtkacrli2kqda",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-12-23T16:01:05.466Z"
        }
      },
      "description": "website",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaasstaqk7xv3zn4vlbczwocr3rrkywhid65bcjpn6ksb4o3i4thwcq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-interactive-compute",
      "time-created": "2024-12-23T16:01:05.516000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanyn5qbo4xvd6qoyhfy3jkf7mthohgjuemttemxojtkacrli2kqda",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-12-23T16:00:57.701Z"
        }
      },
      "description": "website",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaafygtqp3skma5cwn5mjvve5rafdyyifazdoqor4t57qhbe6zyypxa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-interactive-networking",
      "time-created": "2024-12-23T16:00:57.859000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa4lgys6g3puvk3icrap7rmfaxa6mggqxbigoolxvd3sr2ci4tn2oq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:55:57.530Z"
        }
      },
      "description": "prod-kepler",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaabo4purhamrafx4zsprzt5rdxsi7qaypkftcsjwrdewbzrukgceqq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-kepler",
      "time-created": "2024-08-02T04:55:57.549000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaabo4purhamrafx4zsprzt5rdxsi7qaypkftcsjwrdewbzrukgceqq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:58:51.845Z"
        }
      },
      "description": "prod-kepler-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa42jwjcbgcxbbhmt5yox6lyyroiaovm4wra4gh4i37cxqx42tymoa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-kepler-compute",
      "time-created": "2024-08-02T04:58:51.874000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaabo4purhamrafx4zsprzt5rdxsi7qaypkftcsjwrdewbzrukgceqq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:58:59.298Z"
        }
      },
      "description": "prod-kepler-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa5btzob7shlid2fzz57nstl7hy5o2s4mt6wk4wodtcyqdw7qybwwa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-kepler-networking",
      "time-created": "2024-08-02T04:58:59.321000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa4lgys6g3puvk3icrap7rmfaxa6mggqxbigoolxvd3sr2ci4tn2oq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:56:09.875Z"
        }
      },
      "description": "prod-optasia",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaaygfqocgjmlcxeonxyijoqxfm3qhon7grcocmroge46d5uaqb3tpq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-optasia",
      "time-created": "2024-08-02T04:56:09.896000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaaygfqocgjmlcxeonxyijoqxfm3qhon7grcocmroge46d5uaqb3tpq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:59:08.143Z"
        }
      },
      "description": "prod-optasia-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaaqksiwcytfi4zmqd6fbp2mp4ps6lt5p7r7sa27ktspmluivgmmksa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-optasia-compute",
      "time-created": "2024-08-02T04:59:08.176000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaaygfqocgjmlcxeonxyijoqxfm3qhon7grcocmroge46d5uaqb3tpq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:59:15.999Z"
        }
      },
      "description": "prod-optasia-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaaodgug4uqw2aexogmk47qhtqy3f3zxefix4n6qf46p2belcp2nsna",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-optasia-networking",
      "time-created": "2024-08-02T04:59:16.020000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa4lgys6g3puvk3icrap7rmfaxa6mggqxbigoolxvd3sr2ci4tn2oq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:51:31.635Z"
        }
      },
      "description": "prod tamam",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaal475psodxhmbq4rryli4lsv2gyseci4rfpgp2lfmynqpjbyeglza",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-tamam",
      "time-created": "2024-08-02T04:51:31.699000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaal475psodxhmbq4rryli4lsv2gyseci4rfpgp2lfmynqpjbyeglza",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:59:24.748Z"
        }
      },
      "description": "prod-tamam-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa3czfzkvy4dnwbdufxkzwxkhm7bimsiqjsg4t3zphvzaghn7zgo7q",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-tamam-compute",
      "time-created": "2024-08-02T04:59:24.783000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa4lgys6g3puvk3icrap7rmfaxa6mggqxbigoolxvd3sr2ci4tn2oq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-10-21T11:41:48.171Z"
        }
      },
      "description": "cyber soloutions",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaanoberqzqqbsmn4q5bligpjeyfvbls3tagysbdidxvxfvsbht63jq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-tamam-cyber",
      "time-created": "2024-10-21T11:41:48.251000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaal475psodxhmbq4rryli4lsv2gyseci4rfpgp2lfmynqpjbyeglza",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:59:44.396Z"
        }
      },
      "description": "prod-tamam-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaawhbshiohkkv3dcol4e4ayc7q3o7az3kledsylfbttjcjjguxdcxa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-tamam-networking",
      "time-created": "2024-08-02T04:59:44.421000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanzhprubaiftsvlqjeoc6bkmomvsqhpcyqnqr4ffzxk2zs6yghfpa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hashim.algasim@tamam.life",
          "CreatedOn": "2025-06-24T14:09:30.901Z"
        }
      },
      "description": "Testing",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaaavfnhlgwb5bg5im62htgevxtgks3se6io5jkcs2t3e74o4ungova",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "stagging-testing",
      "time-created": "2025-06-24T14:09:30.934000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaaplwesz6cs5qdh3qkecasdphs3dojfe3k2rz6fef6boaps4hgghpa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/ahmad.almamo@tamam.life",
          "CreatedOn": "2023-11-26T12:01:02.637Z"
        }
      },
      "description": "UAT Servers ENV",
      "freeform-tags": {
        "Stagging": ""
      },
      "id": "ocid1.compartment.oc1..aaaaaaaad6xkhrs3fi7j7d5yrof32bp72jt434dzpvcor22dbqj7grpz5kpa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "Stagging_Environment",
      "time-created": "2023-11-26T12:01:02.757000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanzhprubaiftsvlqjeoc6bkmomvsqhpcyqnqr4ffzxk2zs6yghfpa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:28:40.179Z"
        }
      },
      "description": "staging-ad1",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaayudlncts4kbpukdovvbixu2nhw43psfd7kfh2gl3rnfqi5wdxl2q",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-ad1",
      "time-created": "2024-05-30T06:28:40.245000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaayudlncts4kbpukdovvbixu2nhw43psfd7kfh2gl3rnfqi5wdxl2q",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:35:32.227Z"
        }
      },
      "description": "staging-ad1-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaal44jhfhnjmobdmtgsbe2i6zsn3dkocjsxevk4xpxnkkr35imgifq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-ad1-compute",
      "time-created": "2024-05-30T06:35:32.268000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaayudlncts4kbpukdovvbixu2nhw43psfd7kfh2gl3rnfqi5wdxl2q",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:35:42.848Z"
        }
      },
      "description": "staging-ad1-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaapaaf63aqutntd34e2t3bv2wnjgr3stvey3q7xz5bomzdm6ts7yra",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-ad1-networking",
      "time-created": "2024-05-30T06:35:42.860000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanzhprubaiftsvlqjeoc6bkmomvsqhpcyqnqr4ffzxk2zs6yghfpa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:30:23.043Z"
        }
      },
      "description": "Benchmatrix OU",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaanomel4lwvhppnwgu3wqiasvxwz5jv2rrkzzzzj7subfatyrpf3iq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-benchmatrix",
      "time-created": "2024-05-30T06:30:23.077000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanomel4lwvhppnwgu3wqiasvxwz5jv2rrkzzzzj7subfatyrpf3iq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:34:47.110Z"
        }
      },
      "description": "staging-benchmatrix-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaaiywjbjs5k3waqdpgw7egiiocqm2zp3zqixf4qygaus7mcbw4yc3q",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-benchmatrix-compute",
      "time-created": "2024-05-30T06:34:47.178000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanomel4lwvhppnwgu3wqiasvxwz5jv2rrkzzzzj7subfatyrpf3iq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:34:58.020Z"
        }
      },
      "description": "staging-benchmatrix-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa3abpoibvijdcihg4trhozdkywv6f2egvdxhwwnrxgevplyqdgqoq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-benchmatrix-networking",
      "time-created": "2024-05-30T06:34:58.088000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanzhprubaiftsvlqjeoc6bkmomvsqhpcyqnqr4ffzxk2zs6yghfpa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/mutaz.modawy@tamam.life",
          "CreatedOn": "2025-01-16T08:42:13.671Z"
        }
      },
      "description": "staging-cyber",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaaat4kdzdrpsusqavy5lpadsd5v56h6uhrejtbn7nqg5p562do75xa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-cyber",
      "time-created": "2025-01-16T08:42:13.733000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaaat4kdzdrpsusqavy5lpadsd5v56h6uhrejtbn7nqg5p562do75xa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/mutaz.modawy@tamam.life",
          "CreatedOn": "2025-01-16T08:45:14.757Z"
        }
      },
      "description": "staging-cyber-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaafnrdy33re2k5utkbmql7zo7vppiqqzcbuqjwqnniyty5nuuo7xga",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-cyber-compute",
      "time-created": "2025-01-16T08:45:14.811000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaaat4kdzdrpsusqavy5lpadsd5v56h6uhrejtbn7nqg5p562do75xa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/mutaz.modawy@tamam.life",
          "CreatedOn": "2025-01-16T08:46:15.193Z"
        }
      },
      "description": "staging-cyber-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaabs2u5f4geyybmybzwok3ag4d3takwz7qwypwj5fqzf6zsbrchuvq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-cyber-networking",
      "time-created": "2025-01-16T08:46:15.220000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanzhprubaiftsvlqjeoc6bkmomvsqhpcyqnqr4ffzxk2zs6yghfpa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/mutaz.modawy@tamam.life",
          "CreatedOn": "2024-07-28T08:25:47.781Z"
        }
      },
      "description": "DMZ",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaaypuxxv77vq2wyqwngvptyeffwwvzxlksdd3j6lotnbu5o4gcceka",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-dmz",
      "time-created": "2024-07-28T08:25:47.874000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaaypuxxv77vq2wyqwngvptyeffwwvzxlksdd3j6lotnbu5o4gcceka",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/mutaz.modawy@tamam.life",
          "CreatedOn": "2024-08-03T11:43:25.667Z"
        }
      },
      "description": "staging-dmz-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaaqqwdap2scj34mygrbwygjb46qwuksdb2vqgys53t3twyotwxl54q",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-dmz-compute",
      "time-created": "2024-08-03T11:43:25.714000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaaypuxxv77vq2wyqwngvptyeffwwvzxlksdd3j6lotnbu5o4gcceka",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/mutaz.modawy@tamam.life",
          "CreatedOn": "2024-08-03T11:41:38.310Z"
        }
      },
      "description": "staging-dmz-network",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaax7jwgbd2bhtt6p5g22erietjost7kg4cj3zqoqsv6mnbeprxga4a",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-dmz-networking",
      "time-created": "2024-08-03T11:41:38.376000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanzhprubaiftsvlqjeoc6bkmomvsqhpcyqnqr4ffzxk2zs6yghfpa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2025-01-15T11:14:59.042Z"
        }
      },
      "description": "staging-erp",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaadgyn3leijghgbeq2bjndegumu77tegz2fxnjmts4trqzhutn5dua",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-erp",
      "time-created": "2025-01-15T11:14:59.099000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaadgyn3leijghgbeq2bjndegumu77tegz2fxnjmts4trqzhutn5dua",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2025-01-15T11:16:14.047Z"
        }
      },
      "description": "staging-erp-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaarxprk5dgvcgu3seoa4wxk6b7ve6kkqv4i3ieqefkc6t7tlrcdjqa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-erp-compute",
      "time-created": "2025-01-15T11:16:14.098000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaadgyn3leijghgbeq2bjndegumu77tegz2fxnjmts4trqzhutn5dua",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2025-01-15T11:16:03.382Z"
        }
      },
      "description": "staging-erp-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaaogq2lhry6saegbqldhxq3vkcfjhv2rsqjfsmmhrpvqkqbhopy32q",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-erp-networking",
      "time-created": "2025-01-15T11:16:03.437000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanzhprubaiftsvlqjeoc6bkmomvsqhpcyqnqr4ffzxk2zs6yghfpa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:28:49.264Z"
        }
      },
      "description": "Foo OU",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaarfdstjhivdvjem6kkhif22w5l23abixhjx7vyrj6c7yoslb4fztq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-foo",
      "time-created": "2024-05-30T06:28:49.422000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaarfdstjhivdvjem6kkhif22w5l23abixhjx7vyrj6c7yoslb4fztq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:32:11.162Z"
        }
      },
      "description": "staging-foo-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa7k2gzr5zmqpkhgzneg3dl3evil2lzdz4fkfzoeqpvazkobgowkxq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-foo-compute",
      "time-created": "2024-05-30T06:32:11.204000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaarfdstjhivdvjem6kkhif22w5l23abixhjx7vyrj6c7yoslb4fztq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:33:13.998Z"
        }
      },
      "description": "staging-foo-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaanju2f2e25dkvjwfbiso6fpafufgefnmynk74o25jbjgi55iucyma",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-foo-networking",
      "time-created": "2024-05-30T06:33:14.051000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanzhprubaiftsvlqjeoc6bkmomvsqhpcyqnqr4ffzxk2zs6yghfpa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:47:21.123Z"
        }
      },
      "description": "staging-hub",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa4hajzbciyhfudlbafclueyrlxqkxjtmmlinwx4g3dao4uortvltq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-hub",
      "time-created": "2024-05-30T06:47:21.235000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa4hajzbciyhfudlbafclueyrlxqkxjtmmlinwx4g3dao4uortvltq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:47:35.965Z"
        }
      },
      "description": "staging-hub-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaawprlna4ft5tctbbej4yqvzd3f25enzrz674h52zdy3vshn3iijxa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-hub-compute",
      "time-created": "2024-05-30T06:47:36.025000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa4hajzbciyhfudlbafclueyrlxqkxjtmmlinwx4g3dao4uortvltq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:47:50.987Z"
        }
      },
      "description": "staging-hub-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaafrctz77ajkqa6vyozokbz7w4enz6fiisxmzhn4j3tym6smelgasa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-hub-networking",
      "time-created": "2024-05-30T06:47:51.007000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanzhprubaiftsvlqjeoc6bkmomvsqhpcyqnqr4ffzxk2zs6yghfpa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:31:20.189Z"
        }
      },
      "description": "intellect ou",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaagvv7ydx7zaphaefneij6ccsnjcfi3mkhguisbegtls3hn44hz73q",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-intellect",
      "time-created": "2024-05-30T06:31:20.228000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaagvv7ydx7zaphaefneij6ccsnjcfi3mkhguisbegtls3hn44hz73q",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:35:23.009Z"
        }
      },
      "description": "staging-intellect-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa3ayo2n27agscycgvri2v6l4nfs4wnto3j5sgviczlfancxskaowa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-intellect-compute",
      "time-created": "2024-05-30T06:35:23.035000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaagvv7ydx7zaphaefneij6ccsnjcfi3mkhguisbegtls3hn44hz73q",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:35:06.630Z"
        }
      },
      "description": "staging-intellect-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaax2i5ro5cy7exsuq4ybsbrbeexjngncta5ougpvncwktx7blkbdwa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-intellect-networking",
      "time-created": "2024-05-30T06:35:06.683000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanzhprubaiftsvlqjeoc6bkmomvsqhpcyqnqr4ffzxk2zs6yghfpa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-09-05T08:25:14.775Z"
        }
      },
      "description": "born interactive compartment",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa7omu4cnmlyjttydbyh4y2sfeul32ft6b5td2ikw7ij7rw52qnjuq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-interactive",
      "time-created": "2024-09-05T08:25:14.885000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa7omu4cnmlyjttydbyh4y2sfeul32ft6b5td2ikw7ij7rw52qnjuq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-09-05T08:25:35.330Z"
        }
      },
      "description": "born interactive compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaadmr4lj6krewedq47nfz5e5gzki7v5l7pyhv72wfyxv2fsar6lsoq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-interactive-compute",
      "time-created": "2024-09-05T08:25:35.367000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa7omu4cnmlyjttydbyh4y2sfeul32ft6b5td2ikw7ij7rw52qnjuq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-09-05T08:26:26.213Z"
        }
      },
      "description": "born interactive networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaabzwqi35isscd3y6abx3kqc7of2gv2hbvkhil25pqqhy7ncr7n4vq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-interactive-networking",
      "time-created": "2024-09-05T08:26:26.270000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanzhprubaiftsvlqjeoc6bkmomvsqhpcyqnqr4ffzxk2zs6yghfpa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:29:18.197Z"
        }
      },
      "description": "kepler ou",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaaojiggrh6taeci26f44o6qwinbjbn5rxspv6lfzlsxksfclmayncq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-kepler",
      "time-created": "2024-05-30T06:29:18.230000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaaojiggrh6taeci26f44o6qwinbjbn5rxspv6lfzlsxksfclmayncq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:36:09.370Z"
        }
      },
      "description": "staging-kepler-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaagmuyhugxal454coe3zpuhrldefyfld56cbvgprupz244f4yg4vpa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-kepler-compute",
      "time-created": "2024-05-30T06:36:09.404000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaaojiggrh6taeci26f44o6qwinbjbn5rxspv6lfzlsxksfclmayncq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:35:55.755Z"
        }
      },
      "description": "staging-kepler-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaacpure7ii4xzkevm3xdeqbbb5c46laiyllp6x7gcfq2mnvr4bi2tq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-kepler-networking",
      "time-created": "2024-05-30T06:35:55.813000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanzhprubaiftsvlqjeoc6bkmomvsqhpcyqnqr4ffzxk2zs6yghfpa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/abubaker.alderdery@tamam.life",
          "CreatedOn": "2024-10-28T04:38:48.828Z"
        }
      },
      "description": "stage-monitor",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaabb2yiiri5axph44kee26svtjwmng6kz5f2duokqxobxkg46scfwa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-monitor",
      "time-created": "2024-10-28T04:38:49.665000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanzhprubaiftsvlqjeoc6bkmomvsqhpcyqnqr4ffzxk2zs6yghfpa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:31:31.997Z"
        }
      },
      "description": "optasia ou",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaapjs2wxtcepvtcenatqam2hbtqkq6zegq242ut4xexyvxpkp3w7dq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-optasia",
      "time-created": "2024-05-30T06:31:32.049000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaapjs2wxtcepvtcenatqam2hbtqkq6zegq242ut4xexyvxpkp3w7dq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:34:28.563Z"
        }
      },
      "description": "staging-optasia-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa2s6djehfsopfxt6la5vxuwrgr5uh7qikbmkqlmwj7uahiilvr46a",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-optasia-compute",
      "time-created": "2024-05-30T06:34:28.623000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaapjs2wxtcepvtcenatqam2hbtqkq6zegq242ut4xexyvxpkp3w7dq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:34:19.206Z"
        }
      },
      "description": "staging-optasia-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaavd3rycwy3tuplqv7dgycxe6bwk2e2zpjosiij6c5tp3saoxamqqa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-optasia-networking",
      "time-created": "2024-05-30T06:34:19.265000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa4hajzbciyhfudlbafclueyrlxqkxjtmmlinwx4g3dao4uortvltq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/mutaz.modawy@tamam.life",
          "CreatedOn": "2024-08-09T20:40:22.625Z"
        }
      },
      "description": "staging-sec-int-ltm",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa4ic7qq5vfov4si5i7t7ko3hf55sftrq6eehb2wykns64sg7dg5sa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-sec-int-ltm",
      "time-created": "2024-08-09T20:40:22.666000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanzhprubaiftsvlqjeoc6bkmomvsqhpcyqnqr4ffzxk2zs6yghfpa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:29:05.953Z"
        }
      },
      "description": "Tamam OU",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaacx3k5n7o4ryahwtlvmxfa22rgdj73qxovixejon3htlv5ke4pisq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-tamam",
      "time-created": "2024-05-30T06:29:06.014000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaacx3k5n7o4ryahwtlvmxfa22rgdj73qxovixejon3htlv5ke4pisq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:36:39.951Z"
        }
      },
      "description": "staging-tamam-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaaqk7mghokftdtfyaeu4stty3ctkvfem6sjkn7yctc3p3yck4xkvha",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-tamam-compute",
      "time-created": "2024-05-30T06:36:39.988000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaacx3k5n7o4ryahwtlvmxfa22rgdj73qxovixejon3htlv5ke4pisq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:36:47.405Z"
        }
      },
      "description": "staging-tamam-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa57hqs5notxq7gqpzof46lknxlmla4r56d2gkwflgqmingg7y2z5a",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-tamam-networking",
      "time-created": "2024-05-30T06:36:47.457000+00:00"
    },
    {
      "compartment-id": "ocid1.tenancy.oc1..aaaaaaaawotzr2kkpzydktoyolhcgyahaefl4pgec73lkghvmhbphdmhuszq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:48:39.342Z"
        }
      },
      "description": "Tamam Production Enviroment",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa4lgys6g3puvk3icrap7rmfaxa6mggqxbigoolxvd3sr2ci4tn2oq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "tamam-production-env",
      "time-created": "2024-08-02T04:48:39.400000+00:00"
    },
    {
      "compartment-id": "ocid1.tenancy.oc1..aaaaaaaawotzr2kkpzydktoyolhcgyahaefl4pgec73lkghvmhbphdmhuszq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:27:59.643Z"
        }
      },
      "description": "Final Staging Enviroment",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaanzhprubaiftsvlqjeoc6bkmomvsqhpcyqnqr4ffzxk2zs6yghfpa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "tamam-staging-env",
      "time-created": "2024-05-30T06:27:59.941000+00:00"
    },
    {
      "compartment-id": "ocid1.tenancy.oc1..aaaaaaaawotzr2kkpzydktoyolhcgyahaefl4pgec73lkghvmhbphdmhuszq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-01-07T09:56:19.040Z"
        }
      },
      "description": "Contains the different Images of Operating Systems custom uploaded",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaavnybkglsoyjelvwqs2f3o5xvbz2klczbuccgvzxvmafn3nwkmk7q",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "tamam-universal-resources",
      "time-created": "2024-01-07T09:56:19.124000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaaavfnhlgwb5bg5im62htgevxtgks3se6io5jkcs2t3e74o4ungova",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hashim.algasim@tamam.life",
          "CreatedOn": "2025-06-24T14:10:12.664Z"
        }
      },
      "description": "testing-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa4tl67elj5tulzybijhus2gy5tmoqecgaval44tbt2zpzjbcvqwma",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "testing-compute",
      "time-created": "2025-06-24T14:10:12.698000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaaavfnhlgwb5bg5im62htgevxtgks3se6io5jkcs2t3e74o4ungova",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hashim.algasim@tamam.life",
          "CreatedOn": "2025-06-24T14:10:35.208Z"
        }
      },
      "description": "testing-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaagbddcbdwqjbdy3bptvdom322h5p32fcpra2knbwpop3uoji7wr2q",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "testing-networking",
      "time-created": "2025-06-24T14:10:35.225000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaaplwesz6cs5qdh3qkecasdphs3dojfe3k2rz6fef6boaps4hgghpa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/ahmad.almamo@tamam.life",
          "CreatedOn": "2023-11-26T13:37:33.659Z"
        }
      },
      "description": "TAMAM Staging Environment",
      "freeform-tags": {
        "Stagging": ""
      },
      "id": "ocid1.compartment.oc1..aaaaaaaakq7ypj7hvxhvhchcax5eq66oos47nlumkyclmslr3psif3d7uliq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "UAT_Environment",
      "time-created": "2023-11-26T13:37:33.727000+00:00"
    }
  ]
}
```

**Command Executed:**

```bash

```

**Output:**

```
Warning: To increase security of your API key located at C:\Users\hosam\.oci\oci_api_key.pem, append an extra line with 'OCI_API_KEY' at the end. For more information, refer to https://docs.oracle.com/iaas/Content/API/Concepts/apisigningkey.htm. To suppress the warning, set the env variable SUPPRESS_LABEL_WARNING=True
{
  "data": [
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaakq7ypj7hvxhvhchcax5eq66oos47nlumkyclmslr3psif3d7uliq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/ahmad.almamo@tamam.life",
          "CreatedOn": "2023-11-26T13:44:01.648Z"
        }
      },
      "description": "CIS Landing Zone compartment for all resources related to application development: compute instances, storage, functions, OKE, API Gateway, streaming, and others.",
      "freeform-tags": {
        "cis-landing-zone": "CISLZSTG-quickstart/2.6.5\n",
        "cislz-terraform-module": "iam-compartments/0.1.6\n"
      },
      "id": "ocid1.compartment.oc1..aaaaaaaakojkzxzy6ie6ltj4pftujvpkwmjl2b63qddc4u55iwontut3huxq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "CISLZSTG-appdev-cmp",
      "time-created": "2023-11-26T13:44:02.456000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaakq7ypj7hvxhvhchcax5eq66oos47nlumkyclmslr3psif3d7uliq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/ahmad.almamo@tamam.life",
          "CreatedOn": "2023-11-26T13:44:01.797Z"
        }
      },
      "description": "CIS Landing Zone compartment for all database related resources.",
      "freeform-tags": {
        "cis-landing-zone": "CISLZSTG-quickstart/2.6.5\n",
        "cislz-terraform-module": "iam-compartments/0.1.6\n"
      },
      "id": "ocid1.compartment.oc1..aaaaaaaanpyro6gh2xnl2ly7iwfv2swgru5z77k7acqyfvwcabifwkx7zbjq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "CISLZSTG-database-cmp",
      "time-created": "2023-11-26T13:44:02.147000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaakq7ypj7hvxhvhchcax5eq66oos47nlumkyclmslr3psif3d7uliq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/ahmad.almamo@tamam.life",
          "CreatedOn": "2023-11-26T13:44:01.698Z"
        }
      },
      "description": "CIS Landing Zone compartment for all network related resources: VCNs, subnets, network gateways, security lists, NSGs, load balancers, VNICs, and others.",
      "freeform-tags": {
        "cis-landing-zone": "CISLZSTG-quickstart/2.6.5\n",
        "cislz-terraform-module": "iam-compartments/0.1.6\n"
      },
      "id": "ocid1.compartment.oc1..aaaaaaaaxmmq7er5k564ieyszj6zer7keediu4ftqed5b3c67nlami5aajqa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "CISLZSTG-network-cmp",
      "time-created": "2023-11-26T13:44:01.952000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaakq7ypj7hvxhvhchcax5eq66oos47nlumkyclmslr3psif3d7uliq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/ahmad.almamo@tamam.life",
          "CreatedOn": "2023-11-26T13:44:01.690Z"
        }
      },
      "description": "CIS Landing Zone compartment for all security related resources: vaults, topics, notifications, logging, scanning, and others.",
      "freeform-tags": {
        "cis-landing-zone": "CISLZSTG-quickstart/2.6.5\n",
        "cislz-terraform-module": "iam-compartments/0.1.6\n"
      },
      "id": "ocid1.compartment.oc1..aaaaaaaa3v7s2gvjc4yfotbcmttngspxaf3gtabbm6vkhuuusuvegvhdck3q",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "CISLZSTG-security-cmp",
      "time-created": "2023-11-26T13:44:01.735000+00:00"
    },
    {
      "compartment-id": "ocid1.tenancy.oc1..aaaaaaaawotzr2kkpzydktoyolhcgyahaefl4pgec73lkghvmhbphdmhuszq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-07-26T10:49:53.259Z"
        }
      },
      "description": "garbage-collector",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaaplwesz6cs5qdh3qkecasdphs3dojfe3k2rz6fef6boaps4hgghpa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "garbage-collector",
      "time-created": "2024-07-26T10:49:53.488000+00:00"
    },
    {
      "compartment-id": "ocid1.tenancy.oc1..aaaaaaaawotzr2kkpzydktoyolhcgyahaefl4pgec73lkghvmhbphdmhuszq",
      "defined-tags": {},
      "description": "idcs-912bbbb800f7442691c18b5e865c8794|27839004|شركة الاتصالات المتنقلة السعودية",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaay4qtumhpeeiibf3zlbdjqbmhxn2v46klqbvmkghf7mglzxwrii6a",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "ManagedCompartmentForPaaS",
      "time-created": "2023-11-07T09:17:31.269000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaad6xkhrs3fi7j7d5yrof32bp72jt434dzpvcor22dbqj7grpz5kpa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/mutaz.modawy@tamam.life",
          "CreatedOn": "2024-05-17T12:41:41.596Z"
        }
      },
      "description": "Network & Security Compartment",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaadhtfdp545hcia52wep5s7komm2yuivppg3crapd4n6qomqwmi3zq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "N_S-Compartment",
      "time-created": "2024-05-17T12:41:41.708000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaaplwesz6cs5qdh3qkecasdphs3dojfe3k2rz6fef6boaps4hgghpa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-08T01:37:51.235Z"
        }
      },
      "description": "a compartment dedicated for testing concepts and ensuring applicability",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa5qbtywhcuvuqhnecr2cjt3etvgviy6nrsi4nmozl4lt5kd7ndhjq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "oci-poc-comp",
      "time-created": "2024-05-08T01:37:51.293000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa5qbtywhcuvuqhnecr2cjt3etvgviy6nrsi4nmozl4lt5kd7ndhjq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-08T01:39:27.813Z"
        }
      },
      "description": "Compute resources",
      "freeform-tags": {
        "enviroment": "poc"
      },
      "id": "ocid1.compartment.oc1..aaaaaaaaxs64npqx56thybfgmh37nfg4lugn7hdrb7mfby6qwtzz4ien67eq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "poc-compute",
      "time-created": "2024-05-08T01:39:27.863000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa4lgys6g3puvk3icrap7rmfaxa6mggqxbigoolxvd3sr2ci4tn2oq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2025-01-15T11:15:19.513Z"
        }
      },
      "description": "prd-erp",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaafqtqvjw4bttatghqux2aknnf6fmjyuvqg2jarxmeyieyucqigi7a",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prd-erp",
      "time-created": "2025-01-15T11:15:19.565000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaafqtqvjw4bttatghqux2aknnf6fmjyuvqg2jarxmeyieyucqigi7a",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2025-01-15T11:16:27.661Z"
        }
      },
      "description": "prd-erp-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaaohetdfg6rddm3s6wahdv7xzsovbwpkzx4p2nynrmyjtxvwuvhusq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prd-erp-compute",
      "time-created": "2025-01-15T11:16:27.719000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaafqtqvjw4bttatghqux2aknnf6fmjyuvqg2jarxmeyieyucqigi7a",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2025-01-15T11:16:33.823Z"
        }
      },
      "description": "prd-erp-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaatpm2nzpfhpftlayljcw3ixw6wjv5p4eosz6uqksj6j7biqqnjgna",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prd-erp-networking",
      "time-created": "2025-01-15T11:16:33.841000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa4lgys6g3puvk3icrap7rmfaxa6mggqxbigoolxvd3sr2ci4tn2oq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:55:35.969Z"
        }
      },
      "description": "prod-ad1",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaas67uiukraavgczkz2hyaab3gm7p37pp3pujlhdtecu5x4x24ifja",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-ad1",
      "time-created": "2024-08-02T04:55:35.997000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaas67uiukraavgczkz2hyaab3gm7p37pp3pujlhdtecu5x4x24ifja",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:57:06.642Z"
        }
      },
      "description": "prod-ad1-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa3qcqb2sisa6e7yh3mt3flersxe5k6nc2ajlkunkasktynnsstkpa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-ad1-compute",
      "time-created": "2024-08-02T04:57:06.707000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaas67uiukraavgczkz2hyaab3gm7p37pp3pujlhdtecu5x4x24ifja",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:57:16.016Z"
        }
      },
      "description": "prod-ad1-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaak7tubztngmsneexgtmfvpd7wo7xcsnu22o6dh3dv2yqgs76gjryq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-ad1-networking",
      "time-created": "2024-08-02T04:57:16.077000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa4lgys6g3puvk3icrap7rmfaxa6mggqxbigoolxvd3sr2ci4tn2oq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/mutaz.modawy@tamam.life",
          "CreatedOn": "2025-07-31T07:51:32.663Z"
        }
      },
      "description": "prod-audit",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaag2va3um3vf7lcorgxsiucnewnbzjrdt6aelra5kpu45kghtel7xa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-audit",
      "time-created": "2025-07-31T07:51:33.001000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaag2va3um3vf7lcorgxsiucnewnbzjrdt6aelra5kpu45kghtel7xa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/mutaz.modawy@tamam.life",
          "CreatedOn": "2025-07-31T07:54:44.108Z"
        }
      },
      "description": "prod-audit-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaakdesfr2hizxein44p6ohbc4kzalxijeicqudpv4qlv4ezkqm6mbq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-audit-compute",
      "time-created": "2025-07-31T07:54:44.152000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaag2va3um3vf7lcorgxsiucnewnbzjrdt6aelra5kpu45kghtel7xa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/mutaz.modawy@tamam.life",
          "CreatedOn": "2025-07-31T07:55:42.391Z"
        }
      },
      "description": "prod-audit-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaaearqlf2pmjqxcaqbqubcgn772ebyghki6s2mjvohe5mc556rtojq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-audit-networking",
      "time-created": "2025-07-31T07:55:42.478000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa4lgys6g3puvk3icrap7rmfaxa6mggqxbigoolxvd3sr2ci4tn2oq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:55:45.889Z"
        }
      },
      "description": "prod-benchmatrix",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaafp7d5mecyqwnt6vucswmqa5qvm77heggfhsjccs23g2v6nhgi5xq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-benchmatrix",
      "time-created": "2024-08-02T04:55:45.918000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaafp7d5mecyqwnt6vucswmqa5qvm77heggfhsjccs23g2v6nhgi5xq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:57:45.106Z"
        }
      },
      "description": "prod-benchmatrix-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaax5cz2espy4fxpjeaxkwdehy4rh4vgwwxqr6hwlfhgfilpmfz4dyq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-benchmatrix-compute",
      "time-created": "2024-08-02T04:57:45.154000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaafp7d5mecyqwnt6vucswmqa5qvm77heggfhsjccs23g2v6nhgi5xq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:57:58.036Z"
        }
      },
      "description": "prod-benchmatrix-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaacd3sqxcqlusceejueklmp7djit4bycw23gd7pjk7b6mka4zy75yq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-benchmatrix-networking",
      "time-created": "2024-08-02T04:57:58.078000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa4lgys6g3puvk3icrap7rmfaxa6mggqxbigoolxvd3sr2ci4tn2oq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-12-23T15:55:10.311Z"
        }
      },
      "description": "website compartment",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaanyn5qbo4xvd6qoyhfy3jkf7mthohgjuemttemxojtkacrli2kqda",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-born-interactive",
      "time-created": "2024-12-23T15:55:10.377000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanoberqzqqbsmn4q5bligpjeyfvbls3tagysbdidxvxfvsbht63jq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-10-21T11:57:38.914Z"
        }
      },
      "description": "prod-cyber-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaaingfoprklhejxgmi4iioqnon2k5zq32theto545zmfoujzrcodoa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-cyber-compute",
      "time-created": "2024-10-21T11:57:38.968000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanoberqzqqbsmn4q5bligpjeyfvbls3tagysbdidxvxfvsbht63jq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-10-21T11:57:52.912Z"
        }
      },
      "description": "prod-cyber-network",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaaugwikr4obsajq2afls57ilbdja7k54h2353id7ens5acodftntha",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-cyber-networking",
      "time-created": "2024-10-21T11:57:52.943000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa4lgys6g3puvk3icrap7rmfaxa6mggqxbigoolxvd3sr2ci4tn2oq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/mutaz.modawy@tamam.life",
          "CreatedOn": "2024-08-03T11:57:24.380Z"
        }
      },
      "description": "prod-dmz",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaar5ybm7jbocn4ili7mv2nnd2aarcniwk57h3w5vo4vfec57thx32q",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-dmz",
      "time-created": "2024-08-03T11:57:24.455000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaar5ybm7jbocn4ili7mv2nnd2aarcniwk57h3w5vo4vfec57thx32q",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/mutaz.modawy@tamam.life",
          "CreatedOn": "2024-08-03T11:58:09.573Z"
        }
      },
      "description": "prod-dmz-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaarypqho6ibtwcdqj57ldnofbjzz544augsn7ytjzphrn2z5hopm5q",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-dmz-compute",
      "time-created": "2024-08-03T11:58:09.640000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaar5ybm7jbocn4ili7mv2nnd2aarcniwk57h3w5vo4vfec57thx32q",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/mutaz.modawy@tamam.life",
          "CreatedOn": "2024-08-03T11:58:41.778Z"
        }
      },
      "description": "prod-dmz-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaammdxtn6pflccmfhz64e5rnnjq6lxt4vwkgwabmx3ikhbhprv5jta",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-dmz-networking",
      "time-created": "2024-08-03T11:58:41.827000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa4lgys6g3puvk3icrap7rmfaxa6mggqxbigoolxvd3sr2ci4tn2oq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:55:25.596Z"
        }
      },
      "description": "prod-foo",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaanedvgdyty2nkc2m7du6hceenua6bvytzoj4rv2majl3l5wg54ccq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-foo",
      "time-created": "2024-08-02T04:55:25.651000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanedvgdyty2nkc2m7du6hceenua6bvytzoj4rv2majl3l5wg54ccq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:57:26.574Z"
        }
      },
      "description": "prod-foo-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaatws2kz5otltejzfzn5geepibc5y5wpfxhgmg3abgsp2n3rh77iwq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-foo-compute",
      "time-created": "2024-08-02T04:57:26.618000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanedvgdyty2nkc2m7du6hceenua6bvytzoj4rv2majl3l5wg54ccq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:57:34.228Z"
        }
      },
      "description": "prod-foo-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa34lirjyaya7qboejhwzg3jog54mhgcgmh3hgybigsixxtirctq6q",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-foo-networking",
      "time-created": "2024-08-02T04:57:34.262000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa4lgys6g3puvk3icrap7rmfaxa6mggqxbigoolxvd3sr2ci4tn2oq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:56:24.297Z"
        }
      },
      "description": "prod-hub",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaap7d6vntdn3mvbq63gucgn3kh6uf3bwpysxtfpdql7yhdkhujmzka",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-hub",
      "time-created": "2024-08-02T04:56:24.316000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaap7d6vntdn3mvbq63gucgn3kh6uf3bwpysxtfpdql7yhdkhujmzka",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:58:12.013Z"
        }
      },
      "description": "prod-hub-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa2f4qa43tuokkleuakvoirbyhqkthrkm5b6vkabdxefuo66tdjdpq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-hub-compute",
      "time-created": "2024-08-02T04:58:12.052000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaap7d6vntdn3mvbq63gucgn3kh6uf3bwpysxtfpdql7yhdkhujmzka",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:58:20.890Z"
        }
      },
      "description": "prod-hub-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaagchbum3mvn663b6mj5uf4rdni7qloaciinko7fgwl6sorskeqriq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-hub-networking",
      "time-created": "2024-08-02T04:58:20.921000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaap7d6vntdn3mvbq63gucgn3kh6uf3bwpysxtfpdql7yhdkhujmzka",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/mutaz.modawy@tamam.life",
          "CreatedOn": "2024-10-03T12:28:36.854Z"
        }
      },
      "description": "Prod-int-ltm",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa4oseiku73gyj6wxwlrxgszn3vfwq6x3nxnj3y5nktr5uksysacbq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "Prod-int-ltm",
      "time-created": "2024-10-03T12:28:36.914000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa4lgys6g3puvk3icrap7rmfaxa6mggqxbigoolxvd3sr2ci4tn2oq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:56:03.566Z"
        }
      },
      "description": "prod-intellect",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaaaq3tjewk6btvq4ke6dtydphyuzwtvdo455x47y4j6hq45vovvjmq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-intellect",
      "time-created": "2024-08-02T04:56:03.623000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaaaq3tjewk6btvq4ke6dtydphyuzwtvdo455x47y4j6hq45vovvjmq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:58:33.069Z"
        }
      },
      "description": "prod-intellect-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaas4zz2bcg3bhhs2b2haefg4n7iapv7dab7pvne4fhr4uakjqvwx7q",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-intellect-compute",
      "time-created": "2024-08-02T04:58:33.101000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaaaq3tjewk6btvq4ke6dtydphyuzwtvdo455x47y4j6hq45vovvjmq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:58:41.393Z"
        }
      },
      "description": "prod-intellect-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa7utvgyuhtn6afrdtoqqcvwogjgihzp5x5orwwccslx5hpum4golq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-intellect-networking",
      "time-created": "2024-08-02T04:58:41.452000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanyn5qbo4xvd6qoyhfy3jkf7mthohgjuemttemxojtkacrli2kqda",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-12-23T16:01:05.466Z"
        }
      },
      "description": "website",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaasstaqk7xv3zn4vlbczwocr3rrkywhid65bcjpn6ksb4o3i4thwcq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-interactive-compute",
      "time-created": "2024-12-23T16:01:05.516000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanyn5qbo4xvd6qoyhfy3jkf7mthohgjuemttemxojtkacrli2kqda",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-12-23T16:00:57.701Z"
        }
      },
      "description": "website",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaafygtqp3skma5cwn5mjvve5rafdyyifazdoqor4t57qhbe6zyypxa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-interactive-networking",
      "time-created": "2024-12-23T16:00:57.859000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa4lgys6g3puvk3icrap7rmfaxa6mggqxbigoolxvd3sr2ci4tn2oq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:55:57.530Z"
        }
      },
      "description": "prod-kepler",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaabo4purhamrafx4zsprzt5rdxsi7qaypkftcsjwrdewbzrukgceqq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-kepler",
      "time-created": "2024-08-02T04:55:57.549000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaabo4purhamrafx4zsprzt5rdxsi7qaypkftcsjwrdewbzrukgceqq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:58:51.845Z"
        }
      },
      "description": "prod-kepler-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa42jwjcbgcxbbhmt5yox6lyyroiaovm4wra4gh4i37cxqx42tymoa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-kepler-compute",
      "time-created": "2024-08-02T04:58:51.874000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaabo4purhamrafx4zsprzt5rdxsi7qaypkftcsjwrdewbzrukgceqq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:58:59.298Z"
        }
      },
      "description": "prod-kepler-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa5btzob7shlid2fzz57nstl7hy5o2s4mt6wk4wodtcyqdw7qybwwa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-kepler-networking",
      "time-created": "2024-08-02T04:58:59.321000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa4lgys6g3puvk3icrap7rmfaxa6mggqxbigoolxvd3sr2ci4tn2oq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:56:09.875Z"
        }
      },
      "description": "prod-optasia",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaaygfqocgjmlcxeonxyijoqxfm3qhon7grcocmroge46d5uaqb3tpq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-optasia",
      "time-created": "2024-08-02T04:56:09.896000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaaygfqocgjmlcxeonxyijoqxfm3qhon7grcocmroge46d5uaqb3tpq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:59:08.143Z"
        }
      },
      "description": "prod-optasia-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaaqksiwcytfi4zmqd6fbp2mp4ps6lt5p7r7sa27ktspmluivgmmksa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-optasia-compute",
      "time-created": "2024-08-02T04:59:08.176000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaaygfqocgjmlcxeonxyijoqxfm3qhon7grcocmroge46d5uaqb3tpq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:59:15.999Z"
        }
      },
      "description": "prod-optasia-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaaodgug4uqw2aexogmk47qhtqy3f3zxefix4n6qf46p2belcp2nsna",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-optasia-networking",
      "time-created": "2024-08-02T04:59:16.020000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa4lgys6g3puvk3icrap7rmfaxa6mggqxbigoolxvd3sr2ci4tn2oq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:51:31.635Z"
        }
      },
      "description": "prod tamam",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaal475psodxhmbq4rryli4lsv2gyseci4rfpgp2lfmynqpjbyeglza",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-tamam",
      "time-created": "2024-08-02T04:51:31.699000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaal475psodxhmbq4rryli4lsv2gyseci4rfpgp2lfmynqpjbyeglza",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:59:24.748Z"
        }
      },
      "description": "prod-tamam-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa3czfzkvy4dnwbdufxkzwxkhm7bimsiqjsg4t3zphvzaghn7zgo7q",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-tamam-compute",
      "time-created": "2024-08-02T04:59:24.783000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa4lgys6g3puvk3icrap7rmfaxa6mggqxbigoolxvd3sr2ci4tn2oq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-10-21T11:41:48.171Z"
        }
      },
      "description": "cyber soloutions",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaanoberqzqqbsmn4q5bligpjeyfvbls3tagysbdidxvxfvsbht63jq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-tamam-cyber",
      "time-created": "2024-10-21T11:41:48.251000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaal475psodxhmbq4rryli4lsv2gyseci4rfpgp2lfmynqpjbyeglza",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:59:44.396Z"
        }
      },
      "description": "prod-tamam-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaawhbshiohkkv3dcol4e4ayc7q3o7az3kledsylfbttjcjjguxdcxa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "prod-tamam-networking",
      "time-created": "2024-08-02T04:59:44.421000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanzhprubaiftsvlqjeoc6bkmomvsqhpcyqnqr4ffzxk2zs6yghfpa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hashim.algasim@tamam.life",
          "CreatedOn": "2025-06-24T14:09:30.901Z"
        }
      },
      "description": "Testing",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaaavfnhlgwb5bg5im62htgevxtgks3se6io5jkcs2t3e74o4ungova",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "stagging-testing",
      "time-created": "2025-06-24T14:09:30.934000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaaplwesz6cs5qdh3qkecasdphs3dojfe3k2rz6fef6boaps4hgghpa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/ahmad.almamo@tamam.life",
          "CreatedOn": "2023-11-26T12:01:02.637Z"
        }
      },
      "description": "UAT Servers ENV",
      "freeform-tags": {
        "Stagging": ""
      },
      "id": "ocid1.compartment.oc1..aaaaaaaad6xkhrs3fi7j7d5yrof32bp72jt434dzpvcor22dbqj7grpz5kpa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "Stagging_Environment",
      "time-created": "2023-11-26T12:01:02.757000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanzhprubaiftsvlqjeoc6bkmomvsqhpcyqnqr4ffzxk2zs6yghfpa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:28:40.179Z"
        }
      },
      "description": "staging-ad1",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaayudlncts4kbpukdovvbixu2nhw43psfd7kfh2gl3rnfqi5wdxl2q",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-ad1",
      "time-created": "2024-05-30T06:28:40.245000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaayudlncts4kbpukdovvbixu2nhw43psfd7kfh2gl3rnfqi5wdxl2q",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:35:32.227Z"
        }
      },
      "description": "staging-ad1-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaal44jhfhnjmobdmtgsbe2i6zsn3dkocjsxevk4xpxnkkr35imgifq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-ad1-compute",
      "time-created": "2024-05-30T06:35:32.268000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaayudlncts4kbpukdovvbixu2nhw43psfd7kfh2gl3rnfqi5wdxl2q",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:35:42.848Z"
        }
      },
      "description": "staging-ad1-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaapaaf63aqutntd34e2t3bv2wnjgr3stvey3q7xz5bomzdm6ts7yra",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-ad1-networking",
      "time-created": "2024-05-30T06:35:42.860000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanzhprubaiftsvlqjeoc6bkmomvsqhpcyqnqr4ffzxk2zs6yghfpa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:30:23.043Z"
        }
      },
      "description": "Benchmatrix OU",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaanomel4lwvhppnwgu3wqiasvxwz5jv2rrkzzzzj7subfatyrpf3iq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-benchmatrix",
      "time-created": "2024-05-30T06:30:23.077000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanomel4lwvhppnwgu3wqiasvxwz5jv2rrkzzzzj7subfatyrpf3iq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:34:47.110Z"
        }
      },
      "description": "staging-benchmatrix-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaaiywjbjs5k3waqdpgw7egiiocqm2zp3zqixf4qygaus7mcbw4yc3q",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-benchmatrix-compute",
      "time-created": "2024-05-30T06:34:47.178000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanomel4lwvhppnwgu3wqiasvxwz5jv2rrkzzzzj7subfatyrpf3iq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:34:58.020Z"
        }
      },
      "description": "staging-benchmatrix-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa3abpoibvijdcihg4trhozdkywv6f2egvdxhwwnrxgevplyqdgqoq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-benchmatrix-networking",
      "time-created": "2024-05-30T06:34:58.088000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanzhprubaiftsvlqjeoc6bkmomvsqhpcyqnqr4ffzxk2zs6yghfpa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/mutaz.modawy@tamam.life",
          "CreatedOn": "2025-01-16T08:42:13.671Z"
        }
      },
      "description": "staging-cyber",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaaat4kdzdrpsusqavy5lpadsd5v56h6uhrejtbn7nqg5p562do75xa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-cyber",
      "time-created": "2025-01-16T08:42:13.733000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaaat4kdzdrpsusqavy5lpadsd5v56h6uhrejtbn7nqg5p562do75xa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/mutaz.modawy@tamam.life",
          "CreatedOn": "2025-01-16T08:45:14.757Z"
        }
      },
      "description": "staging-cyber-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaafnrdy33re2k5utkbmql7zo7vppiqqzcbuqjwqnniyty5nuuo7xga",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-cyber-compute",
      "time-created": "2025-01-16T08:45:14.811000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaaat4kdzdrpsusqavy5lpadsd5v56h6uhrejtbn7nqg5p562do75xa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/mutaz.modawy@tamam.life",
          "CreatedOn": "2025-01-16T08:46:15.193Z"
        }
      },
      "description": "staging-cyber-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaabs2u5f4geyybmybzwok3ag4d3takwz7qwypwj5fqzf6zsbrchuvq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-cyber-networking",
      "time-created": "2025-01-16T08:46:15.220000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanzhprubaiftsvlqjeoc6bkmomvsqhpcyqnqr4ffzxk2zs6yghfpa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/mutaz.modawy@tamam.life",
          "CreatedOn": "2024-07-28T08:25:47.781Z"
        }
      },
      "description": "DMZ",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaaypuxxv77vq2wyqwngvptyeffwwvzxlksdd3j6lotnbu5o4gcceka",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-dmz",
      "time-created": "2024-07-28T08:25:47.874000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaaypuxxv77vq2wyqwngvptyeffwwvzxlksdd3j6lotnbu5o4gcceka",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/mutaz.modawy@tamam.life",
          "CreatedOn": "2024-08-03T11:43:25.667Z"
        }
      },
      "description": "staging-dmz-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaaqqwdap2scj34mygrbwygjb46qwuksdb2vqgys53t3twyotwxl54q",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-dmz-compute",
      "time-created": "2024-08-03T11:43:25.714000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaaypuxxv77vq2wyqwngvptyeffwwvzxlksdd3j6lotnbu5o4gcceka",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/mutaz.modawy@tamam.life",
          "CreatedOn": "2024-08-03T11:41:38.310Z"
        }
      },
      "description": "staging-dmz-network",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaax7jwgbd2bhtt6p5g22erietjost7kg4cj3zqoqsv6mnbeprxga4a",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-dmz-networking",
      "time-created": "2024-08-03T11:41:38.376000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanzhprubaiftsvlqjeoc6bkmomvsqhpcyqnqr4ffzxk2zs6yghfpa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2025-01-15T11:14:59.042Z"
        }
      },
      "description": "staging-erp",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaadgyn3leijghgbeq2bjndegumu77tegz2fxnjmts4trqzhutn5dua",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-erp",
      "time-created": "2025-01-15T11:14:59.099000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaadgyn3leijghgbeq2bjndegumu77tegz2fxnjmts4trqzhutn5dua",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2025-01-15T11:16:14.047Z"
        }
      },
      "description": "staging-erp-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaarxprk5dgvcgu3seoa4wxk6b7ve6kkqv4i3ieqefkc6t7tlrcdjqa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-erp-compute",
      "time-created": "2025-01-15T11:16:14.098000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaadgyn3leijghgbeq2bjndegumu77tegz2fxnjmts4trqzhutn5dua",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2025-01-15T11:16:03.382Z"
        }
      },
      "description": "staging-erp-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaaogq2lhry6saegbqldhxq3vkcfjhv2rsqjfsmmhrpvqkqbhopy32q",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-erp-networking",
      "time-created": "2025-01-15T11:16:03.437000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanzhprubaiftsvlqjeoc6bkmomvsqhpcyqnqr4ffzxk2zs6yghfpa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:28:49.264Z"
        }
      },
      "description": "Foo OU",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaarfdstjhivdvjem6kkhif22w5l23abixhjx7vyrj6c7yoslb4fztq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-foo",
      "time-created": "2024-05-30T06:28:49.422000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaarfdstjhivdvjem6kkhif22w5l23abixhjx7vyrj6c7yoslb4fztq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:32:11.162Z"
        }
      },
      "description": "staging-foo-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa7k2gzr5zmqpkhgzneg3dl3evil2lzdz4fkfzoeqpvazkobgowkxq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-foo-compute",
      "time-created": "2024-05-30T06:32:11.204000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaarfdstjhivdvjem6kkhif22w5l23abixhjx7vyrj6c7yoslb4fztq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:33:13.998Z"
        }
      },
      "description": "staging-foo-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaanju2f2e25dkvjwfbiso6fpafufgefnmynk74o25jbjgi55iucyma",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-foo-networking",
      "time-created": "2024-05-30T06:33:14.051000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanzhprubaiftsvlqjeoc6bkmomvsqhpcyqnqr4ffzxk2zs6yghfpa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:47:21.123Z"
        }
      },
      "description": "staging-hub",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa4hajzbciyhfudlbafclueyrlxqkxjtmmlinwx4g3dao4uortvltq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-hub",
      "time-created": "2024-05-30T06:47:21.235000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa4hajzbciyhfudlbafclueyrlxqkxjtmmlinwx4g3dao4uortvltq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:47:35.965Z"
        }
      },
      "description": "staging-hub-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaawprlna4ft5tctbbej4yqvzd3f25enzrz674h52zdy3vshn3iijxa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-hub-compute",
      "time-created": "2024-05-30T06:47:36.025000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa4hajzbciyhfudlbafclueyrlxqkxjtmmlinwx4g3dao4uortvltq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:47:50.987Z"
        }
      },
      "description": "staging-hub-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaafrctz77ajkqa6vyozokbz7w4enz6fiisxmzhn4j3tym6smelgasa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-hub-networking",
      "time-created": "2024-05-30T06:47:51.007000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanzhprubaiftsvlqjeoc6bkmomvsqhpcyqnqr4ffzxk2zs6yghfpa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:31:20.189Z"
        }
      },
      "description": "intellect ou",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaagvv7ydx7zaphaefneij6ccsnjcfi3mkhguisbegtls3hn44hz73q",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-intellect",
      "time-created": "2024-05-30T06:31:20.228000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaagvv7ydx7zaphaefneij6ccsnjcfi3mkhguisbegtls3hn44hz73q",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:35:23.009Z"
        }
      },
      "description": "staging-intellect-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa3ayo2n27agscycgvri2v6l4nfs4wnto3j5sgviczlfancxskaowa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-intellect-compute",
      "time-created": "2024-05-30T06:35:23.035000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaagvv7ydx7zaphaefneij6ccsnjcfi3mkhguisbegtls3hn44hz73q",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:35:06.630Z"
        }
      },
      "description": "staging-intellect-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaax2i5ro5cy7exsuq4ybsbrbeexjngncta5ougpvncwktx7blkbdwa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-intellect-networking",
      "time-created": "2024-05-30T06:35:06.683000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanzhprubaiftsvlqjeoc6bkmomvsqhpcyqnqr4ffzxk2zs6yghfpa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-09-05T08:25:14.775Z"
        }
      },
      "description": "born interactive compartment",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa7omu4cnmlyjttydbyh4y2sfeul32ft6b5td2ikw7ij7rw52qnjuq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-interactive",
      "time-created": "2024-09-05T08:25:14.885000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa7omu4cnmlyjttydbyh4y2sfeul32ft6b5td2ikw7ij7rw52qnjuq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-09-05T08:25:35.330Z"
        }
      },
      "description": "born interactive compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaadmr4lj6krewedq47nfz5e5gzki7v5l7pyhv72wfyxv2fsar6lsoq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-interactive-compute",
      "time-created": "2024-09-05T08:25:35.367000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa7omu4cnmlyjttydbyh4y2sfeul32ft6b5td2ikw7ij7rw52qnjuq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-09-05T08:26:26.213Z"
        }
      },
      "description": "born interactive networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaabzwqi35isscd3y6abx3kqc7of2gv2hbvkhil25pqqhy7ncr7n4vq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-interactive-networking",
      "time-created": "2024-09-05T08:26:26.270000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanzhprubaiftsvlqjeoc6bkmomvsqhpcyqnqr4ffzxk2zs6yghfpa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:29:18.197Z"
        }
      },
      "description": "kepler ou",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaaojiggrh6taeci26f44o6qwinbjbn5rxspv6lfzlsxksfclmayncq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-kepler",
      "time-created": "2024-05-30T06:29:18.230000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaaojiggrh6taeci26f44o6qwinbjbn5rxspv6lfzlsxksfclmayncq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:36:09.370Z"
        }
      },
      "description": "staging-kepler-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaagmuyhugxal454coe3zpuhrldefyfld56cbvgprupz244f4yg4vpa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-kepler-compute",
      "time-created": "2024-05-30T06:36:09.404000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaaojiggrh6taeci26f44o6qwinbjbn5rxspv6lfzlsxksfclmayncq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:35:55.755Z"
        }
      },
      "description": "staging-kepler-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaacpure7ii4xzkevm3xdeqbbb5c46laiyllp6x7gcfq2mnvr4bi2tq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-kepler-networking",
      "time-created": "2024-05-30T06:35:55.813000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanzhprubaiftsvlqjeoc6bkmomvsqhpcyqnqr4ffzxk2zs6yghfpa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/abubaker.alderdery@tamam.life",
          "CreatedOn": "2024-10-28T04:38:48.828Z"
        }
      },
      "description": "stage-monitor",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaabb2yiiri5axph44kee26svtjwmng6kz5f2duokqxobxkg46scfwa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-monitor",
      "time-created": "2024-10-28T04:38:49.665000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanzhprubaiftsvlqjeoc6bkmomvsqhpcyqnqr4ffzxk2zs6yghfpa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:31:31.997Z"
        }
      },
      "description": "optasia ou",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaapjs2wxtcepvtcenatqam2hbtqkq6zegq242ut4xexyvxpkp3w7dq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-optasia",
      "time-created": "2024-05-30T06:31:32.049000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaapjs2wxtcepvtcenatqam2hbtqkq6zegq242ut4xexyvxpkp3w7dq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:34:28.563Z"
        }
      },
      "description": "staging-optasia-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa2s6djehfsopfxt6la5vxuwrgr5uh7qikbmkqlmwj7uahiilvr46a",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-optasia-compute",
      "time-created": "2024-05-30T06:34:28.623000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaapjs2wxtcepvtcenatqam2hbtqkq6zegq242ut4xexyvxpkp3w7dq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:34:19.206Z"
        }
      },
      "description": "staging-optasia-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaavd3rycwy3tuplqv7dgycxe6bwk2e2zpjosiij6c5tp3saoxamqqa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-optasia-networking",
      "time-created": "2024-05-30T06:34:19.265000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaa4hajzbciyhfudlbafclueyrlxqkxjtmmlinwx4g3dao4uortvltq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/mutaz.modawy@tamam.life",
          "CreatedOn": "2024-08-09T20:40:22.625Z"
        }
      },
      "description": "staging-sec-int-ltm",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa4ic7qq5vfov4si5i7t7ko3hf55sftrq6eehb2wykns64sg7dg5sa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-sec-int-ltm",
      "time-created": "2024-08-09T20:40:22.666000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaanzhprubaiftsvlqjeoc6bkmomvsqhpcyqnqr4ffzxk2zs6yghfpa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:29:05.953Z"
        }
      },
      "description": "Tamam OU",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaacx3k5n7o4ryahwtlvmxfa22rgdj73qxovixejon3htlv5ke4pisq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-tamam",
      "time-created": "2024-05-30T06:29:06.014000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaacx3k5n7o4ryahwtlvmxfa22rgdj73qxovixejon3htlv5ke4pisq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:36:39.951Z"
        }
      },
      "description": "staging-tamam-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaaqk7mghokftdtfyaeu4stty3ctkvfem6sjkn7yctc3p3yck4xkvha",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-tamam-compute",
      "time-created": "2024-05-30T06:36:39.988000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaacx3k5n7o4ryahwtlvmxfa22rgdj73qxovixejon3htlv5ke4pisq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:36:47.405Z"
        }
      },
      "description": "staging-tamam-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa57hqs5notxq7gqpzof46lknxlmla4r56d2gkwflgqmingg7y2z5a",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "staging-tamam-networking",
      "time-created": "2024-05-30T06:36:47.457000+00:00"
    },
    {
      "compartment-id": "ocid1.tenancy.oc1..aaaaaaaawotzr2kkpzydktoyolhcgyahaefl4pgec73lkghvmhbphdmhuszq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-08-02T04:48:39.342Z"
        }
      },
      "description": "Tamam Production Enviroment",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa4lgys6g3puvk3icrap7rmfaxa6mggqxbigoolxvd3sr2ci4tn2oq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "tamam-production-env",
      "time-created": "2024-08-02T04:48:39.400000+00:00"
    },
    {
      "compartment-id": "ocid1.tenancy.oc1..aaaaaaaawotzr2kkpzydktoyolhcgyahaefl4pgec73lkghvmhbphdmhuszq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-05-30T06:27:59.643Z"
        }
      },
      "description": "Final Staging Enviroment",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaanzhprubaiftsvlqjeoc6bkmomvsqhpcyqnqr4ffzxk2zs6yghfpa",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "tamam-staging-env",
      "time-created": "2024-05-30T06:27:59.941000+00:00"
    },
    {
      "compartment-id": "ocid1.tenancy.oc1..aaaaaaaawotzr2kkpzydktoyolhcgyahaefl4pgec73lkghvmhbphdmhuszq",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hossam.ismat@tamam.life",
          "CreatedOn": "2024-01-07T09:56:19.040Z"
        }
      },
      "description": "Contains the different Images of Operating Systems custom uploaded",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaavnybkglsoyjelvwqs2f3o5xvbz2klczbuccgvzxvmafn3nwkmk7q",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "tamam-universal-resources",
      "time-created": "2024-01-07T09:56:19.124000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaaavfnhlgwb5bg5im62htgevxtgks3se6io5jkcs2t3e74o4ungova",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hashim.algasim@tamam.life",
          "CreatedOn": "2025-06-24T14:10:12.664Z"
        }
      },
      "description": "testing-compute",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaa4tl67elj5tulzybijhus2gy5tmoqecgaval44tbt2zpzjbcvqwma",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "testing-compute",
      "time-created": "2025-06-24T14:10:12.698000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaaavfnhlgwb5bg5im62htgevxtgks3se6io5jkcs2t3e74o4ungova",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/hashim.algasim@tamam.life",
          "CreatedOn": "2025-06-24T14:10:35.208Z"
        }
      },
      "description": "testing-networking",
      "freeform-tags": {},
      "id": "ocid1.compartment.oc1..aaaaaaaagbddcbdwqjbdy3bptvdom322h5p32fcpra2knbwpop3uoji7wr2q",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "testing-networking",
      "time-created": "2025-06-24T14:10:35.225000+00:00"
    },
    {
      "compartment-id": "ocid1.compartment.oc1..aaaaaaaaplwesz6cs5qdh3qkecasdphs3dojfe3k2rz6fef6boaps4hgghpa",
      "defined-tags": {
        "Oracle-Tags": {
          "CreatedBy": "default/ahmad.almamo@tamam.life",
          "CreatedOn": "2023-11-26T13:37:33.659Z"
        }
      },
      "description": "TAMAM Staging Environment",
      "freeform-tags": {
        "Stagging": ""
      },
      "id": "ocid1.compartment.oc1..aaaaaaaakq7ypj7hvxhvhchcax5eq66oos47nlumkyclmslr3psif3d7uliq",
      "inactive-status": null,
      "is-accessible": null,
      "lifecycle-state": "ACTIVE",
      "name": "UAT_Environment",
      "time-created": "2023-11-26T13:37:33.727000+00:00"
    }
  ]
}
```

USER:
with ocid 

AGENT:

## Complete Compartment Hierarchy with OCIDs

### Root Level

```
tamam (tenancy)
ocid1.tenancy.oc1..aaaaaaaawotzr2kkpzydktoyolhcgyahaefl4pgec73lkghvmhbphdmhuszq
```

---

### garbage-collector

`ocid1.compartment.oc1..aaaaaaaaplwesz6cs5qdh3qkecasdphs3dojfe3k2rz6fef6boaps4hgghpa`

- **oci-poc-comp** `ocid1.compartment.oc1..aaaaaaaa5qbtywhcuvuqhnecr2cjt3etvgviy6nrsi4nmozl4lt5kd7ndhjq`
  - poc-compute `ocid1.compartment.oc1..aaaaaaaaxs64npqx56thybfgmh37nfg4lugn7hdrb7mfby6qwtzz4ien67eq`
- **Stagging_Environment** `ocid1.compartment.oc1..aaaaaaaad6xkhrs3fi7j7d5yrof32bp72jt434dzpvcor22dbqj7grpz5kpa`
  - N_S-Compartment `ocid1.compartment.oc1..aaaaaaaadhtfdp545hcia52wep5s7komm2yuivppg3crapd4n6qomqwmi3zq`
- **UAT_Environment** `ocid1.compartment.oc1..aaaaaaaakq7ypj7hvxhvhchcax5eq66oos47nlumkyclmslr3psif3d7uliq`
  - CISLZSTG-appdev-cmp `ocid1.compartment.oc1..aaaaaaaakojkzxzy6ie6ltj4pftujvpkwmjl2b63qddc4u55iwontut3huxq`
  - CISLZSTG-database-cmp `ocid1.compartment.oc1..aaaaaaaanpyro6gh2xnl2ly7iwfv2swgru5z77k7acqyfvwcabifwkx7zbjq`
  - CISLZSTG-network-cmp `ocid1.compartment.oc1..aaaaaaaaxmmq7er5k564ieyszj6zer7keediu4ftqed5b3c67nlami5aajqa`
  - CISLZSTG-security-cmp `ocid1.compartment.oc1..aaaaaaaa3v7s2gvjc4yfotbcmttngspxaf3gtabbm6vkhuuusuvegvhdck3q`

---

### ManagedCompartmentForPaaS

`ocid1.compartment.oc1..aaaaaaaay4qtumhpeeiibf3zlbdjqbmhxn2v46klqbvmkghf7mglzxwrii6a`

---

### tamam-production-env ⭐

`ocid1.compartment.oc1..aaaaaaaa4lgys6g3puvk3icrap7rmfaxa6mggqxbigoolxvd3sr2ci4tn2oq`


| Compartment                   | OCID                                                                                  |
| ----------------------------- | ------------------------------------------------------------------------------------- |
| **prd-erp**                   | `ocid1.compartment.oc1..aaaaaaaafqtqvjw4bttatghqux2aknnf6fmjyuvqg2jarxmeyieyucqigi7a` |
| └ prd-erp-compute             | `ocid1.compartment.oc1..aaaaaaaaohetdfg6rddm3s6wahdv7xzsovbwpkzx4p2nynrmyjtxvwuvhusq` |
| └ prd-erp-networking          | `ocid1.compartment.oc1..aaaaaaaatpm2nzpfhpftlayljcw3ixw6wjv5p4eosz6uqksj6j7biqqnjgna` |
| **prod-ad1**                  | `ocid1.compartment.oc1..aaaaaaaas67uiukraavgczkz2hyaab3gm7p37pp3pujlhdtecu5x4x24ifja` |
| └ prod-ad1-compute            | `ocid1.compartment.oc1..aaaaaaaa3qcqb2sisa6e7yh3mt3flersxe5k6nc2ajlkunkasktynnsstkpa` |
| └ prod-ad1-networking         | `ocid1.compartment.oc1..aaaaaaaak7tubztngmsneexgtmfvpd7wo7xcsnu22o6dh3dv2yqgs76gjryq` |
| **prod-audit**                | `ocid1.compartment.oc1..aaaaaaaag2va3um3vf7lcorgxsiucnewnbzjrdt6aelra5kpu45kghtel7xa` |
| └ prod-audit-compute          | `ocid1.compartment.oc1..aaaaaaaakdesfr2hizxein44p6ohbc4kzalxijeicqudpv4qlv4ezkqm6mbq` |
| └ prod-audit-networking       | `ocid1.compartment.oc1..aaaaaaaaearqlf2pmjqxcaqbqubcgn772ebyghki6s2mjvohe5mc556rtojq` |
| **prod-benchmatrix**          | `ocid1.compartment.oc1..aaaaaaaafp7d5mecyqwnt6vucswmqa5qvm77heggfhsjccs23g2v6nhgi5xq` |
| └ prod-benchmatrix-compute    | `ocid1.compartment.oc1..aaaaaaaax5cz2espy4fxpjeaxkwdehy4rh4vgwwxqr6hwlfhgfilpmfz4dyq` |
| └ prod-benchmatrix-networking | `ocid1.compartment.oc1..aaaaaaaacd3sqxcqlusceejueklmp7djit4bycw23gd7pjk7b6mka4zy75yq` |
| **prod-born-interactive**     | `ocid1.compartment.oc1..aaaaaaaanyn5qbo4xvd6qoyhfy3jkf7mthohgjuemttemxojtkacrli2kqda` |
| └ prod-interactive-compute    | `ocid1.compartment.oc1..aaaaaaaasstaqk7xv3zn4vlbczwocr3rrkywhid65bcjpn6ksb4o3i4thwcq` |
| └ prod-interactive-networking | `ocid1.compartment.oc1..aaaaaaaafygtqp3skma5cwn5mjvve5rafdyyifazdoqor4t57qhbe6zyypxa` |
| **prod-dmz**                  | `ocid1.compartment.oc1..aaaaaaaar5ybm7jbocn4ili7mv2nnd2aarcniwk57h3w5vo4vfec57thx32q` |
| └ prod-dmz-compute            | `ocid1.compartment.oc1..aaaaaaaarypqho6ibtwcdqj57ldnofbjzz544augsn7ytjzphrn2z5hopm5q` |
| └ prod-dmz-networking         | `ocid1.compartment.oc1..aaaaaaaammdxtn6pflccmfhz64e5rnnjq6lxt4vwkgwabmx3ikhbhprv5jta` |
| **prod-foo**                  | `ocid1.compartment.oc1..aaaaaaaanedvgdyty2nkc2m7du6hceenua6bvytzoj4rv2majl3l5wg54ccq` |
| └ prod-foo-compute            | `ocid1.compartment.oc1..aaaaaaaatws2kz5otltejzfzn5geepibc5y5wpfxhgmg3abgsp2n3rh77iwq` |
| └ prod-foo-networking         | `ocid1.compartment.oc1..aaaaaaaa34lirjyaya7qboejhwzg3jog54mhgcgmh3hgybigsixxtirctq6q` |
| **prod-hub**                  | `ocid1.compartment.oc1..aaaaaaaap7d6vntdn3mvbq63gucgn3kh6uf3bwpysxtfpdql7yhdkhujmzka` |
| └ prod-hub-compute            | `ocid1.compartment.oc1..aaaaaaaa2f4qa43tuokkleuakvoirbyhqkthrkm5b6vkabdxefuo66tdjdpq` |
| └ prod-hub-networking         | `ocid1.compartment.oc1..aaaaaaaagchbum3mvn663b6mj5uf4rdni7qloaciinko7fgwl6sorskeqriq` |
| └ Prod-int-ltm                | `ocid1.compartment.oc1..aaaaaaaa4oseiku73gyj6wxwlrxgszn3vfwq6x3nxnj3y5nktr5uksysacbq` |
| **prod-intellect**            | `ocid1.compartment.oc1..aaaaaaaaaq3tjewk6btvq4ke6dtydphyuzwtvdo455x47y4j6hq45vovvjmq` |
| └ prod-intellect-compute      | `ocid1.compartment.oc1..aaaaaaaas4zz2bcg3bhhs2b2haefg4n7iapv7dab7pvne4fhr4uakjqvwx7q` |
| └ prod-intellect-networking   | `ocid1.compartment.oc1..aaaaaaaa7utvgyuhtn6afrdtoqqcvwogjgihzp5x5orwwccslx5hpum4golq` |
| **prod-kepler**               | `ocid1.compartment.oc1..aaaaaaaabo4purhamrafx4zsprzt5rdxsi7qaypkftcsjwrdewbzrukgceqq` |
| └ prod-kepler-compute         | `ocid1.compartment.oc1..aaaaaaaa42jwjcbgcxbbhmt5yox6lyyroiaovm4wra4gh4i37cxqx42tymoa` |
| └ prod-kepler-networking      | `ocid1.compartment.oc1..aaaaaaaa5btzob7shlid2fzz57nstl7hy5o2s4mt6wk4wodtcyqdw7qybwwa` |
| **prod-optasia**              | `ocid1.compartment.oc1..aaaaaaaaygfqocgjmlcxeonxyijoqxfm3qhon7grcocmroge46d5uaqb3tpq` |
| └ prod-optasia-compute        | `ocid1.compartment.oc1..aaaaaaaaqksiwcytfi4zmqd6fbp2mp4ps6lt5p7r7sa27ktspmluivgmmksa` |
| └ prod-optasia-networking     | `ocid1.compartment.oc1..aaaaaaaaodgug4uqw2aexogmk47qhtqy3f3zxefix4n6qf46p2belcp2nsna` |
| **prod-tamam**                | `ocid1.compartment.oc1..aaaaaaaal475psodxhmbq4rryli4lsv2gyseci4rfpgp2lfmynqpjbyeglza` |
| └ prod-tamam-compute          | `ocid1.compartment.oc1..aaaaaaaa3czfzkvy4dnwbdufxkzwxkhm7bimsiqjsg4t3zphvzaghn7zgo7q` |
| └ prod-tamam-networking       | `ocid1.compartment.oc1..aaaaaaaawhbshiohkkv3dcol4e4ayc7q3o7az3kledsylfbttjcjjguxdcxa` |
| **prod-tamam-cyber**          | `ocid1.compartment.oc1..aaaaaaaanoberqzqqbsmn4q5bligpjeyfvbls3tagysbdidxvxfvsbht63jq` |
| └ prod-cyber-compute          | `ocid1.compartment.oc1..aaaaaaaaingfoprklhejxgmi4iioqnon2k5zq32theto545zmfoujzrcodoa` |
| └ prod-cyber-networking       | `ocid1.compartment.oc1..aaaaaaaaugwikr4obsajq2afls57ilbdja7k54h2353id7ens5acodftntha` |


---

### tamam-staging-env

`ocid1.compartment.oc1..aaaaaaaanzhprubaiftsvlqjeoc6bkmomvsqhpcyqnqr4ffzxk2zs6yghfpa`


| Compartment                      | OCID                                                                                  |
| -------------------------------- | ------------------------------------------------------------------------------------- |
| **staging-ad1**                  | `ocid1.compartment.oc1..aaaaaaaayudlncts4kbpukdovvbixu2nhw43psfd7kfh2gl3rnfqi5wdxl2q` |
| └ staging-ad1-compute            | `ocid1.compartment.oc1..aaaaaaaal44jhfhnjmobdmtgsbe2i6zsn3dkocjsxevk4xpxnkkr35imgifq` |
| └ staging-ad1-networking         | `ocid1.compartment.oc1..aaaaaaaapaaf63aqutntd34e2t3bv2wnjgr3stvey3q7xz5bomzdm6ts7yra` |
| **staging-benchmatrix**          | `ocid1.compartment.oc1..aaaaaaaanomel4lwvhppnwgu3wqiasvxwz5jv2rrkzzzzj7subfatyrpf3iq` |
| └ staging-benchmatrix-compute    | `ocid1.compartment.oc1..aaaaaaaaiywjbjs5k3waqdpgw7egiiocqm2zp3zqixf4qygaus7mcbw4yc3q` |
| └ staging-benchmatrix-networking | `ocid1.compartment.oc1..aaaaaaaa3abpoibvijdcihg4trhozdkywv6f2egvdxhwwnrxgevplyqdgqoq` |
| **staging-cyber**                | `ocid1.compartment.oc1..aaaaaaaaat4kdzdrpsusqavy5lpadsd5v56h6uhrejtbn7nqg5p562do75xa` |
| └ staging-cyber-compute          | `ocid1.compartment.oc1..aaaaaaaafnrdy33re2k5utkbmql7zo7vppiqqzcbuqjwqnniyty5nuuo7xga` |
| └ staging-cyber-networking       | `ocid1.compartment.oc1..aaaaaaaabs2u5f4geyybmybzwok3ag4d3takwz7qwypwj5fqzf6zsbrchuvq` |
| **staging-dmz**                  | `ocid1.compartment.oc1..aaaaaaaaypuxxv77vq2wyqwngvptyeffwwvzxlksdd3j6lotnbu5o4gcceka` |
| └ staging-dmz-compute            | `ocid1.compartment.oc1..aaaaaaaaqqwdap2scj34mygrbwygjb46qwuksdb2vqgys53t3twyotwxl54q` |
| └ staging-dmz-networking         | `ocid1.compartment.oc1..aaaaaaaax7jwgbd2bhtt6p5g22erietjost7kg4cj3zqoqsv6mnbeprxga4a` |
| **staging-erp**                  | `ocid1.compartment.oc1..aaaaaaaadgyn3leijghgbeq2bjndegumu77tegz2fxnjmts4trqzhutn5dua` |
| └ staging-erp-compute            | `ocid1.compartment.oc1..aaaaaaaarxprk5dgvcgu3seoa4wxk6b7ve6kkqv4i3ieqefkc6t7tlrcdjqa` |
| └ staging-erp-networking         | `ocid1.compartment.oc1..aaaaaaaaogq2lhry6saegbqldhxq3vkcfjhv2rsqjfsmmhrpvqkqbhopy32q` |
| **staging-foo**                  | `ocid1.compartment.oc1..aaaaaaaarfdstjhivdvjem6kkhif22w5l23abixhjx7vyrj6c7yoslb4fztq` |
| └ staging-foo-compute            | `ocid1.compartment.oc1..aaaaaaaa7k2gzr5zmqpkhgzneg3dl3evil2lzdz4fkfzoeqpvazkobgowkxq` |
| └ staging-foo-networking         | `ocid1.compartment.oc1..aaaaaaaanju2f2e25dkvjwfbiso6fpafufgefnmynk74o25jbjgi55iucyma` |
| **staging-hub**                  | `ocid1.compartment.oc1..aaaaaaaa4hajzbciyhfudlbafclueyrlxqkxjtmmlinwx4g3dao4uortvltq` |
| └ staging-hub-compute            | `ocid1.compartment.oc1..aaaaaaaawprlna4ft5tctbbej4yqvzd3f25enzrz674h52zdy3vshn3iijxa` |
| └ staging-hub-networking         | `ocid1.compartment.oc1..aaaaaaaafrctz77ajkqa6vyozokbz7w4enz6fiisxmzhn4j3tym6smelgasa` |
| └ staging-sec-int-ltm            | `ocid1.compartment.oc1..aaaaaaaa4ic7qq5vfov4si5i7t7ko3hf55sftrq6eehb2wykns64sg7dg5sa` |
| **staging-intellect**            | `ocid1.compartment.oc1..aaaaaaaagvv7ydx7zaphaefneij6ccsnjcfi3mkhguisbegtls3hn44hz73q` |
| └ staging-intellect-compute      | `ocid1.compartment.oc1..aaaaaaaa3ayo2n27agscycgvri2v6l4nfs4wnto3j5sgviczlfancxskaowa` |
| └ staging-intellect-networking   | `ocid1.compartment.oc1..aaaaaaaax2i5ro5cy7exsuq4ybsbrbeexjngncta5ougpvncwktx7blkbdwa` |
| **staging-interactive**          | `ocid1.compartment.oc1..aaaaaaaa7omu4cnmlyjttydbyh4y2sfeul32ft6b5td2ikw7ij7rw52qnjuq` |
| └ staging-interactive-compute    | `ocid1.compartment.oc1..aaaaaaaadmr4lj6krewedq47nfz5e5gzki7v5l7pyhv72wfyxv2fsar6lsoq` |
| └ staging-interactive-networking | `ocid1.compartment.oc1..aaaaaaaabzwqi35isscd3y6abx3kqc7of2gv2hbvkhil25pqqhy7ncr7n4vq` |
| **staging-kepler**               | `ocid1.compartment.oc1..aaaaaaaaojiggrh6taeci26f44o6qwinbjbn5rxspv6lfzlsxksfclmayncq` |
| └ staging-kepler-compute         | `ocid1.compartment.oc1..aaaaaaaagmuyhugxal454coe3zpuhrldefyfld56cbvgprupz244f4yg4vpa` |
| └ staging-kepler-networking      | `ocid1.compartment.oc1..aaaaaaaacpure7ii4xzkevm3xdeqbbb5c46laiyllp6x7gcfq2mnvr4bi2tq` |
| **staging-monitor**              | `ocid1.compartment.oc1..aaaaaaaabb2yiiri5axph44kee26svtjwmng6kz5f2duokqxobxkg46scfwa` |
| **staging-optasia**              | `ocid1.compartment.oc1..aaaaaaaapjs2wxtcepvtcenatqam2hbtqkq6zegq242ut4xexyvxpkp3w7dq` |
| └ staging-optasia-compute        | `ocid1.compartment.oc1..aaaaaaaa2s6djehfsopfxt6la5vxuwrgr5uh7qikbmkqlmwj7uahiilvr46a` |
| └ staging-optasia-networking     | `ocid1.compartment.oc1..aaaaaaaavd3rycwy3tuplqv7dgycxe6bwk2e2zpjosiij6c5tp3saoxamqqa` |
| **staging-tamam**                | `ocid1.compartment.oc1..aaaaaaaacx3k5n7o4ryahwtlvmxfa22rgdj73qxovixejon3htlv5ke4pisq` |
| └ staging-tamam-compute          | `ocid1.compartment.oc1..aaaaaaaaqk7mghokftdtfyaeu4stty3ctkvfem6sjkn7yctc3p3yck4xkvha` |
| └ staging-tamam-networking       | `ocid1.compartment.oc1..aaaaaaaa57hqs5notxq7gqpzof46lknxlmla4r56d2gkwflgqmingg7y2z5a` |
| **stagging-testing**             | `ocid1.compartment.oc1..aaaaaaaaavfnhlgwb5bg5im62htgevxtgks3se6io5jkcs2t3e74o4ungova` |
| └ testing-compute                | `ocid1.compartment.oc1..aaaaaaaa4tl67elj5tulzybijhus2gy5tmoqecgaval44tbt2zpzjbcvqwma` |
| └ testing-networking             | `ocid1.compartment.oc1..aaaaaaaagbddcbdwqjbdy3bptvdom322h5p32fcpra2knbwpop3uoji7wr2q` |


---

### tamam-universal-resources

`ocid1.compartment.oc1..aaaaaaaavnybkglsoyjelvwqs2f3o5xvbz2klczbuccgvzxvmafn3nwkmk7q`

Subagent: 98a72004-3551-4181-9f5f-a12d47e66aa5