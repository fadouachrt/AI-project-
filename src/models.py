import random 

THIRD_DAY_OPTION = ["Wednesday", "Thursday", "Sunday"]
ROUND_DAYS = ["Friday", "Saturday"]

class Match:
    def __init__ ( self , home , away , day = None ) :
        self.home = home 
        self.away = away 
        self.day = day 
        # self.is_derby = away.name in home.derby_rivals

    def __repr__ (self) :
        return f"{self.home} (H) vs {self.away} | {self.day} "


class Round:
    def __init__ ( self , round_index , matches = None ):
        self.round_index = round_index 
        self.matches = matches if matches is not None else []
        self.third_day = random.choice( THIRD_DAY_OPTION )
        self.days = ROUND_DAYS + [self.third_day]
        
    def __repr__ ( self ):
        return f" Round {self.round_index + 1 } | Days : {self.days} | Matches : {len(self.matches)}"
    
class Schedule:
    def __init__ ( self , rounds = None , teams = None):
        self.rounds = rounds if rounds is not None else []
        self.teams = teams if teams is not None else []
        
    def total_rounds( self ) : 
        return len( self.rounds )
    
    def total_matches ( self ):
        return sum( len(r.matches) for r in self.rounds )
    
    def print_schedule ( self ) : 
        for r in self.rounds:
            print(f"\n--- Round {r.round_index + 1} | Days: {r.days} ---")
            for match in r.matches:
                print(f"  {match}")
                

    
    