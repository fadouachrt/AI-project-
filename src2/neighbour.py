import copy 
import random 
from models import Match , Round , Schedule

def swap_rounds ( schedule , round_i , round_j ) : 
    new_schedule = copy.deepcopy ( schedule )
    
    new_schedule.rounds[round_i].matches , new_schedule.rounds[round_j].matches = new_schedule.rounds[round_j].matches , new_schedule.rounds[round_i].matches
    
    new_schedule.rounds[round_i].round_index = round_i
    new_schedule.rounds[round_j].round_index = round_j
    
    return new_schedule

def swap_home_away ( schedule , round_i , match_i ):
    new_schedule = copy.deepcopy ( schedule )
    n = len ( new_schedule.rounds )
    half = n // 2
    
    match = new_schedule.rounds [ round_i ].matches [ match_i ]
    
    match.home , match.away = match.away , match.home 
    
    if round_i < half : 
        mirror_i = round_i + half    
    else : 
        mirror_i = round_i - half 
        
    mirror_round = new_schedule.rounds [ mirror_i ]
    
    for m in mirror_round.matches : 
        if m.pair() == match.pair() : 
            m.home , m.away = m.away , m.home 
            break 
        
    return new_schedule
    

def swap_days_in_round ( schedule , round_i , match_i_a , match_i_b ):
    new_schedule = copy.deepcopy ( schedule )
    round_obj = new_schedule.rounds[round_i]
    
    round_obj.matches[match_i_a].day , round_obj.matches[match_i_b].day = round_obj.matches[match_i_b].day , round_obj.matches[match_i_a].day
    
    return new_schedule

def swap_third_day ( schedule , round_i , round_j ) : 
    new_schedule = copy.deepcopy ( schedule )
    
    round_a = new_schedule.rounds [ round_i ]
    round_b = new_schedule.rounds [ round_j ]
    
    old_third_a = round_a.third_day
    old_third_b = round_b.third_day
    
    round_a.third_day , round_b.third_day = old_third_b , old_third_a
    
    round_a.days = ["Friday", "Saturday", round_a.third_day]
    round_b.days = ["Friday", "Saturday", round_b.third_day]
    
    for match in round_a.matches : 
        if match.day == old_third_a : 
            match.day = round_a.third_day
            break     
    for match in round_b.matches : 
        if match.day == old_third_b : 
            match.day = round_b.third_day
            break 
        
    return new_schedule

def generate_all_neighbours ( schedule ) : 
    neighbours = []
    n = len ( schedule.rounds )
    
    for i in range ( n ) : 
        for j in range ( i + 1 , n ) : 
            neighbours.append( swap_rounds ( schedule , i , j ) ) 
            
    
    for i , r in enumerate ( schedule.rounds ) : 
        for m_inx in range ( len( r.matches )) :
            neighbours.append ( swap_home_away ( schedule , i , m_inx))
            
    for i , r in enumerate ( schedule.rounds ) :
        for ma_inx in range ( len ( r.matches )) : 
            for mb_inx in range ( ma_inx + 1 , len ( r.matches)) : 
                neighbours.append ( swap_days_in_round ( schedule , i , ma_inx , mb_inx))
                
    for i in range ( n ) : 
        for j in range ( i + 1 , n ) : 
            neighbours.append ( swap_third_day ( schedule , i , j ))
            
    return neighbours

def generate_one_random_neighbor(schedule):
    n = len(schedule.rounds)
    move = random.choice([1, 2, 3, 4])

    if move == 1:
        i, j = random.sample(range(n), 2)
        return swap_rounds(schedule, i, j)

    elif move == 2:
        i = random.randint(0, n - 1)
        m_idx = random.randint(0, len(schedule.rounds[i].matches) - 1)
        return swap_home_away(schedule, i, m_idx)

    elif move == 3:
        i = random.randint(0, n - 1)
        n_matches = len(schedule.rounds[i].matches)
        a, b = random.sample(range(n_matches), 2)
        return swap_days_in_round (schedule, i, a, b)

    elif move == 4:
        i, j = random.sample(range(n), 2)
        return swap_third_day(schedule, i, j)
         
         

    
    
