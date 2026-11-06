#include "game.hpp"
#include <iostream>
#include <stdexcept>
void check(bool ok,const char* message) { if(!ok) throw std::runtime_error(message); }
int main() {
    runner::Game g; g.random.seed(42); g.start(); g.spawn=100;
    g.update(0.05f,1,0); check(g.x>480,"movement");
    g.x=940; g.update(0.05f,1,0); check(g.x==940,"boundary");
    g.objects={{g.x,g.y,12,0,true}}; g.update(0,0,0);
    check(g.score==10 && g.best==10 && g.objects.empty(),"collect star once");
    g.pause(); const float y=g.y; g.update(0.05f,0,1); check(g.y==y,"pause freezes simulation");
    g.pause(); g.objects={{g.x,g.y,20,0,false}}; g.update(0,0,0); check(g.state==runner::State::Over,"asteroid collision");
    g.start(); check(g.score==0 && g.best==10 && g.objects.empty(),"restart preserves record");
    g.spawn=0; g.update(0.05f,0,0); check(g.objects.size()==1,"spawn");
    std::cout<<"All gameplay tests passed\n";
}
