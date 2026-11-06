CREATE OR REPLACE VIEW electricity_research_monthly AS  
SELECT p.date,
    p.value AS electricity_price,
    c.value AS utility_capacity,
    u.value AS capacity_utilization,
    t.value AS total_power_construction,
    pr.value AS private_power_construction,
    pb.value AS public_power_construction,
    td.value AS transmission_distribution_activity
   FROM observations p
     LEFT JOIN observations c ON p.date = c.date AND c.series_id = 'CAPG2211S'
     LEFT JOIN observations u ON p.date = u.date AND u.series_id = 'CAPUTLG2211S'
     LEFT JOIN observations t ON p.date = t.date AND t.series_id = 'TLPWRCONS'
     LEFT JOIN observations pr ON p.date = pr.date AND pr.series_id = 'PRPWRCONS'
     LEFT JOIN observations pb ON p.date = pb.date AND pb.series_id = 'PBPWRCONS'
     LEFT JOIN observations td ON p.date = td.date AND td.series_id = 'IPG22112S'
  WHERE p.series_id = 'APU000072610' 
     AND p.date >= '2002-01-01'
  ;
