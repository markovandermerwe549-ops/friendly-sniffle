#pragma once
#include <algorithm>
#include <cmath>
#include <random>
#include <vector>
namespace runner {
struct Object { float x, y, radius, speed; bool star; };
enum class State { Menu, Playing, Paused, Over };
struct Game {
    State state = State::Menu;
    float x = 480, y = 460, elapsed = 0, spawn = 0;
    int score = 0, best = 0;
    std::vector<Object> objects;
    std::mt19937 random{std::random_device{}()};
    float roll(float low, float high) { return std::uniform_real_distribution<float>(low, high)(random); }
    void start() { x=480; y=460; elapsed=0; spawn=0; score=0; objects.clear(); state=State::Playing; }
    void pause() { if(state==State::Playing) state=State::Paused; else if(state==State::Paused) state=State::Playing; }
    void update(float dt, float dx, float dy) {
        if(state!=State::Playing) return;
        dt=std::clamp(dt, 0.0f, 0.05f);
        const float length=std::hypot(dx,dy);
        if(length>0) { x+=dx/length*390*dt; y+=dy/length*390*dt; }
        x=std::clamp(x,20.0f,940.0f); y=std::clamp(y,95.0f,575.0f);
        elapsed+=dt; spawn-=dt;
        if(spawn<=0) {
            bool star=roll(0,1)<0.32f;
            objects.push_back({roll(30,930),-30,star?12.0f:roll(18,29),roll(120,190)+std::min(elapsed*4,280.0f),star});
            spawn=std::max(0.16f,0.52f-elapsed*0.004f);
        }
        for(auto& o:objects) {
            o.y+=o.speed*dt;
            if(std::hypot(o.x-x,o.y-y)<o.radius+12) {
                if(o.star) { score+=10; best=std::max(best,score); o.y=700; }
                else { state=State::Over; return; }
            }
        }
        objects.erase(std::remove_if(objects.begin(),objects.end(),[](const Object& o){return o.y>650;}),objects.end());
    }
};
}
