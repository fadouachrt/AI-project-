
THIRD_DAY_OPTION = ["Wednesday", "Thursday", "Sunday"]
ROUND_DAYS = ["Friday", "Saturday"]

class Team:
    def __init__ (self, name, lat, lon):
        self.name = name
        self.lat = lat
        self.lon = lon

    def repr(self):
        return f"Team({self.name})"
class Match:
    def __init__ ( self , home , away , day = None ) :
        self.home = home 
        self.away = away 
        self.day = day 

    def __repr__ (self) :
        return f"{self.home.name} (H) vs {self.away.name} | {self.day} "

    def pair ( self ) :
        return frozenset ( {self.home.name , self.away.name })
    
    def ordered_pair ( self ) : 
        return ( self.home.name , self.away.name , self.day  )
class Round:
    def __init__ ( self , round_index , matches = None ):
        self.round_index = round_index 
        self.matches = matches if matches is not None else []
        self.third_day = THIRD_DAY_OPTION [ round_index % len ( THIRD_DAY_OPTION ) ]
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
                

    
    
