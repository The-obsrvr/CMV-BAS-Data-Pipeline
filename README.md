# Data Processing Pipeline for transforming ChangeMyView Reddit Conversations to Bipolar Argument Structures

This repository contains documentation on a project that forms part of a broader PhD research effort titled "Identifying the Stance of Argumentative Opinions in Political Discourse", conducted under the HYBRIDS Project within the Horizon Europe framework.

The primary contributor and point of contact for this repository is Siddharth Bhargava (sbhargava@fbk.eu).

---

## Overview


### Motivation





---

## Data Pipeline

This project uses data from the publicly available [Webis ChangeMyView Corpus 2020](https://zenodo.org/records/3778298). The corpus contains all posts and comments from the ChangeMyView subreddit, covering the period from **2005 to September 2017**.

We extract structured debate threads with the following properties:

- Each thread starts with an **Original Post (OP)** that introduces a discussion topic.
- Threads are **tree-structured conversations** consisting of replies and nested interactions.

Each conversation is categorized based on whether the OP changes their view:

- **Delta threads (positive outcome)**  
  The OP awards a *delta* (∆), indicating that their viewpoint has changed.

- **Non-delta threads (negative outcome)**  
  No delta is awarded. These threads are **truncated maximum up to the comment containing the 500th sentence** to due to computational limitation. Truncation is applied **only to non-delta threads**.

### Conversational Thread Selection Criteria

We identify relevant discussions using keyword-based filtering. Specifically, threads are selected if they primarily focus on Euro-centric political issues such as:

- Migration / migration crisis  
- Euroscepticism / European integration  
- Climate crisis
- Health 

Exceptions for made to non-euro-centric instances in case sufficient euro-centric instances are not identified.

The other structural constraints include:

- Limiting to conversations having upto 500 sentences.
- Positive and negative samples are relatively balanced in size.
- Selection process is additionally complemented with semantic relevance to ensure topic alignment.

### Filtering and Cleaning

Following cleaning/filtering steps have been performed: 

- **Temporal / length filtering**  
  Only comments posted **before the delta event timestamp** (for positive threads) or up to the comment containing the **500th sentence** (for non-delta threads) are retained.

- **Privacy & anonymization**  
  This work does not perform any form of user profiling or behavioral analysis.  
  All user identifiers have been replaced with pseudonyms to reduce direct traceability of personal data.  
  ⚠️ Note: Since the data originates from a public source, comments may still be reverse-traceable when cross-referenced with the original dataset.

- **Removed & deleted content handling**  
  The ChangeMyView subreddit is a heavily moderated community with a [strict set of rules](https://www.reddit.com/r/changemyview/wiki/rules/). As a result, some posts or comments may be removed by moderators or alternatively, the comment could be deleted by its owner directly. These exist in the original Webis-CMV-20 Corpus.
  To preserve the **conversation structure** in our dataset, such entries are retained in their removed form and explicitly marked as `"deleted"`.  
  However, these entries are **excluded from argument structure modeling** where the system skips this particular point in the discussion and continues with analysing the next comment in line.

- **Mentions & quotations handling**  
  Mentions are preserved but replaced with their pseudonymized equivalents.  
  Quotations from earlier comments are retained and explicitly marked in the format:  
  `previously stated: "..."`

- **Text normalization**  
  Comments are cleaned to remove non-ASCII characters, URLs, emojis, and other non-textual objects.

Prior to length-wise filtering and semantic topic-filtering, 65169 submission(s) were identified in the raw file covering 602,726 thread(s).

Post applying length filtering (minimum 10 comments excluding OP) and semantic filtering (to identify euro-centric posts or migration/health/climate) posts, we get 


### Reformatting Thread format to paragraph format

To standardize the conversational structure and make it suited for computational modeling, each thread is transformed into a **flattened paragraph format**:

- **Depth-first traversal**  
  Comments are ordered using a depth-first strategy. Starting from the main branch, any newly emerging branch is fully traversed before returning to the parent thread. 

- **Preserved reply structure**  
  The reply relationships between speakers are explicitly retained using inline annotations.  
  Each comment is prefixed with a structured tag indicating the interaction, for example:  
  `[Speaker 2 replying to Speaker 1]: ...`

This approach preserves conversational context while producing a linearized representation suitable for downstream modeling.

## Argument Structure Prediction

For more details on the argument structure prediction process, refer to our modeling pipeline repository: 

---

## Final Dataset Description

Each conversation has been stored in the following JSON format:

```json
[
{
  "meta_info": {
    "subreddit": "",
    "post_title": "",
    "opening_post": ""
  },
  "disc_id": 0,
  "thread_id": 0,
  "unique_id": 0,
  "original_thread_format": "",
  "flatted_format": "",
  "true_cmv_status": "yes / no"
  },
  "..."
  ]
```
###### add Example

---

## Exploratory Data Analysis: A Brief Report

---

## Acknowledgements 

This research work has received funding from the European Union's Horizon Europe research and innovation programme under the Marie Skłodowska-Curie Grant Agreement No. 101073351. Views and opinions expressed are however those of the author(s) only and do not necessarily reflect those of the European Union or European Research Executive Agency (REA). Neither the European Union nor the granting authority can be held responsible for them.


---

## Citation

tbd 



