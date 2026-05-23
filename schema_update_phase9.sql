-- ============================================================
-- Phase 9 Schema Update: Seeding Batch 2 Institutions
-- Execute this script in your Supabase SQL Editor.
-- ============================================================

INSERT INTO institutions (name, slug, description, website, location)
VALUES
    (
        'Krishna Kanta Handiqui State Open University', 
        'krishna-kanta-handiqui-state-open-university', 
        'Krishna Kanta Handiqui State Open University (KKHSOU) is a state university located in Guwahati, Assam, India. It was established in 2005 as the first open university in Northeast India.', 
        'https://kkhsou.ac.in', 
        'Guwahati, Assam, India'
    ),
    (
        'Assam Women''s University', 
        'assam-womens-university', 
        'Assam Women''s University (AWU) is a state university located in Jorhat, Assam, India. It was established in 2013 by the Government of Assam to promote higher education for women.', 
        'https://awu.ac.in', 
        'Jorhat, Assam, India'
    ),
    (
        'Numaligarh Refinery Limited', 
        'numaligarh-refinery-limited', 
        'Numaligarh Refinery Limited (NRL) is a public sector oil company located in Numaligarh, Golaghat district, Assam, India. It is a subsidiary of Oil India Limited.', 
        'https://www.nrl.co.in', 
        'Numaligarh, Golaghat, Assam'
    ),
    (
        'assamJOBnews', 
        'assamjobnews', 
        'Aggregated local job board and educational news portal sourcing private and public sector opportunities across Assam.', 
        'https://www.assamjobnews.in', 
        'Assam, India'
    )
ON CONFLICT (slug) DO UPDATE
SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    website = EXCLUDED.website,
    location = EXCLUDED.location;
