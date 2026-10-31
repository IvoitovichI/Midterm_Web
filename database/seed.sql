-- Applied once, in the same transaction as schema.sql. Deleted logs stay deleted.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM app_metadata WHERE key = 'initial_seed_v1') THEN
        INSERT INTO wanted_criminals
            (id, name, nickname, reward, latitude, longitude, location_note, difficulty, armed, has_crew, escape_master)
        OVERRIDING SYSTEM VALUE VALUES
            (1, 'Kael Voss', 'Void Reaper', 25000, 12.45, -45.67, 'Dock 7, Titan station', 9, TRUE, TRUE, TRUE),
            (2, NULL, 'Ghost', 12000, NULL, NULL, 'Last seen near the Orion nebula', 8, FALSE, FALSE, TRUE),
            (3, 'Mira Sol', 'Red Comet', 7500, -22.10, 88.30, NULL, 6, TRUE, FALSE, TRUE),
            (4, 'Drax Nox', 'Iron Fang', 5000, NULL, NULL, 'Asteroid belt, abandoned mining ship', 5, TRUE, TRUE, FALSE),
            (5, 'Tali Ren', 'Star Pickpocket', 1500, 0, 15.25, 'Luna market', 2, FALSE, FALSE, FALSE);
        INSERT INTO hunt_logs (criminal_id, success, notes) VALUES
            (1, FALSE, 'Target escaped during a boarding attempt.'),
            (1, FALSE, 'Crew forced us to retreat from Titan station.'),
            (2, FALSE, 'Only a decoy signal was found in the nebula.'),
            (2, TRUE, 'Captured at an abandoned relay station.'),
            (3, FALSE, 'Target escaped through an asteroid field.'),
            (3, TRUE, 'Engine disabled; target captured without injury.'),
            (4, FALSE, 'Armored crew blocked the docking tunnel.'),
            (4, TRUE, 'Captured after negotiating with the crew.'),
            (5, FALSE, 'Lost the target in the Luna market.'),
            (5, TRUE, 'Captured near the shuttle terminal.');
        PERFORM setval(pg_get_serial_sequence('wanted_criminals', 'id'), (SELECT MAX(id) FROM wanted_criminals));
        INSERT INTO app_metadata(key) VALUES ('initial_seed_v1');
    END IF;
END $$;
