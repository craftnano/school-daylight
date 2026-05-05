# Phase 3R — Step 5: Current Flag Metadata Prose

Verbatim dump of `what_it_means`, `what_it_might_not_mean`, and `parent_question` strings from `flag_thresholds.yaml`. One section per flag, sub-sections per color.

## chronic_absenteeism

- field: `derived.chronic_absenteeism_pct`
- yellow threshold: **0.2**
- red threshold: **0.3**
- threshold_source: USED chronic absenteeism benchmarks (20% yellow, 30% red); aligned with federal Every Student Succeeds Act reporting thresholds and foundation document v0.2.

### yellow

**what_it_means:**

> More than 20% of students at this school are chronically absent, meaning they miss 10% or more of school days. This is above the threshold researchers identify as a warning sign for academic outcomes.

**what_it_might_not_mean:**

> Chronic absenteeism reflects many factors beyond school quality, including family health crises, transportation barriers, housing instability, and community-wide events. A high rate does not necessarily indicate a school climate problem.

**parent_question:**

> What programs does the school have to support students with attendance challenges, and how has the trend changed over the past two years?

### red

**what_it_means:**

> More than 30% of students at this school are chronically absent. At this level, a significant share of students are missing enough school to meaningfully affect their learning outcomes.

**what_it_might_not_mean:**

> Chronic absenteeism reflects many factors beyond school quality, including family health crises, transportation barriers, housing instability, and community-wide events. A high rate does not necessarily indicate a school climate problem.

**parent_question:**

> What is the school doing to address chronic absenteeism, and are there specific supports available for families facing attendance barriers?

## counselor_ratio

- field: `derived.counselor_student_ratio`
- yellow threshold: **400**
- red threshold: **500**
- threshold_source: American School Counselor Association (ASCA) recommends a maximum ratio of 1:250. Thresholds of 1:400 (yellow) and 1:500 (red) are set conservatively above the recommendation; foundation document v0.2.

### yellow

**what_it_means:**

> This school has more than 400 students per counselor, well above the ASCA-recommended maximum of 250:1. Students may have limited access to academic, social-emotional, and college/career counseling.

**what_it_might_not_mean:**

> Some schools supplement counselor roles with other support staff (social workers, psychologists, community partners) not captured in this ratio. The ratio alone does not tell you whether students feel supported.

**parent_question:**

> How does my child access counseling support, and are there other support staff (social workers, mentors) available beyond the school counselor?

### red

**what_it_means:**

> This school has more than 500 students per counselor. At this level, meaningful individual counseling is very difficult to provide. Research links high counselor caseloads to lower college enrollment rates and reduced social-emotional support.

**what_it_might_not_mean:**

> Some schools supplement counselor roles with other support staff (social workers, psychologists, community partners) not captured in this ratio. The ratio alone does not tell you whether students feel supported.

**parent_question:**

> Does the school have plans to add counseling capacity, and what alternative support resources are available to students?

## discipline_disparity

- field: `derived.discipline_disparity_max`
- yellow threshold: **2.0**
- red threshold: **3.0**
- threshold_source: Discipline disparity ratio compares suspension rates of each racial group to white students. A ratio of 2.0 means a group is suspended at twice the rate. Thresholds aligned with OCR enforcement guidance and ProPublica Miseducation methodology; foundation document v0.2.

### yellow

**what_it_means:**

> At least one racial group at this school is suspended at more than twice the rate of white students. This pattern is common nationwide but warrants attention as a potential equity concern.

**what_it_might_not_mean:**

> Disparity ratios do not prove discrimination. Differences may reflect referral patterns, policy implementation, community factors, or small sample sizes that amplify individual incidents. The ratio identifies a pattern worth investigating, not a conclusion.

**parent_question:**

> Is the school aware of differences in discipline rates across student groups, and what steps are being taken to ensure equitable discipline practices?

### red

**what_it_means:**

> At least one racial group at this school is suspended at more than three times the rate of white students. This level of disparity is a significant equity concern that federal civil rights guidance identifies as warranting investigation.

**what_it_might_not_mean:**

> Disparity ratios do not prove discrimination. Differences may reflect referral patterns, policy implementation, community factors, or small sample sizes that amplify individual incidents. The CRDC data is from 2021-22 and may not reflect current practices.

**parent_question:**

> Has the school conducted a discipline equity audit, and what specific changes have been made to address disparities in suspension rates?

## no_counselor

- field: `staffing.counselor_fte`
- condition: `equals_zero`
- threshold_source: CRDC staffing data reports 0.0 counselor FTE for this school.

### yellow

_(no `yellow` block defined for this flag)_

### red

**what_it_means:**

> This school reports zero counselor staff. Students at this school do not have access to a dedicated school counselor for academic, social-emotional, or college/career guidance.

**what_it_might_not_mean:**

> Some schools share counselors with other buildings or contract counseling services that may not appear in staffing reports. The school may also use other support models (social workers, community partnerships) not captured in this data.

**parent_question:**

> How does the school provide counseling and social-emotional support to students without a dedicated counselor on staff?
