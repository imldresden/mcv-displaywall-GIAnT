// GIAnT Group Interaction Analysis Toolkit
// Copyright (C) 2017 Interactive Media Lab Dresden
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

#include "User.h"

#include "Path.h"

using namespace std;

Touch::Touch(int userid, const glm::vec2& pos, float time, float duration, bool injected, std::string type)
    : m_UserID(userid),
      m_Pos(pos),
      m_Time(time),
      m_Duration(duration),
      m_Injected(injected),
      m_Type(type)
{
}

const glm::vec2& Touch::getPos() const
{
    return m_Pos;
}

float Touch::getTime() const
{
    return m_Time;
}

float Touch::getDuration() const
{
    return m_Duration;
}

bool Touch::getInjected() const
{
    return m_Injected;
}

std::string Touch::getTType() const
{
    return m_Type;
}


DeviceEntry::DeviceEntry(int userid, const glm::vec2& screenPos, const glm::vec3& spacePos, const glm::vec3& orientation, double time)
    : m_UserID(userid),
      m_ScreenPos(screenPos),
      m_SpacePos(spacePos),
      m_Orientation(orientation),
      m_Time(time)
{
}

const int DeviceEntry::getUserID() const
{
    return m_UserID;
}

void DeviceEntry::setWallViewpoint(const glm::vec2& pt)
{
    m_WallViewpoint = pt;
}

const glm::vec2& DeviceEntry::getScreenPos() const
{
    return m_ScreenPos;
}

const glm::vec3& DeviceEntry::getSpacePos() const
{
    return m_SpacePos;
}

const glm::vec3& DeviceEntry::getOrientation() const
{
    return m_Orientation;
}

double DeviceEntry::getTime() const
{
    return m_Time;
}

const glm::vec2& DeviceEntry::getWallViewpoint() const
{
    return m_WallViewpoint;
}


User::User(int userid, float duration)
    : m_UserID(userid),
      m_Duration(duration)
{
}

User::~User()
{
}

void User::addHeadData(const HeadData& head)
{
    m_HeadData.push_back(head);
}

void User::addTouch(const Touch& touch)
{
    m_Touches.push_back(touch);
}

void User::addDeviceTouch(const Touch& touch)
{
    m_DeviceTouches.push_back(touch);
}

void User::addDeviceEntry(const DeviceEntry& deviceEntry)
{
    m_DeviceEntries.push_back(deviceEntry);
}

int User::getUserID() const
{
    return m_UserID;
}

const int User::getHeadInfoCount() const
{
    return m_HeadData.size();
}

const int User::getDeviceEntryInfoCount() const
{
    return m_DeviceEntries.size();
}

const glm::vec3& User::getHeadPos(float time) const
{
    int i = timeToIndexHead(time);
    return m_HeadData[i].getPos();
}

const glm::vec2& User::getWallViewpoint(float time) const
{
    int i = timeToIndexHead(time);
    return m_HeadData[i].getWallViewpoint();
}

const glm::vec2& User::getDeviceWallViewpoint(float time) const
{
    int i = timeToIndexDevice(time);
    return m_DeviceEntries[i].getWallViewpoint();
}

const glm::vec3& User::getHeadRot(float time) const
{
    int i = timeToIndexHead(time);
    return m_HeadData[i].getRot();
}

const HeadData User::getHeadData(float time) const
{
    int i = timeToIndexHead(time);
    return m_HeadData[i];
}

const DeviceEntry User::getDeviceEntry(float time) const
{
    int i = timeToIndexDevice(time);
    return m_DeviceEntries[i];
}

glm::vec3 User::getHeadPosAvg(float time, int smoothness) const
{
    int i = timeToIndexHead(time);
    glm::vec3 startSum = m_HeadData[fmax(0, i - smoothness/2)].getPosPrefixSum();
    glm::vec3 endSum = m_HeadData[fmin(m_HeadData.size()-1, i + int((smoothness+1)/2))].getPosPrefixSum();
    glm::vec3 headPos = glm::vec3(
            (endSum.x - startSum.x) / smoothness,
            (endSum.y - startSum.y) / smoothness,
            (endSum.z - startSum.z) / smoothness);
    return headPos;
}

float User::getDistTravelled(float startTime, float endTime) const
{
    int start_i = timeToIndexHead(startTime);
    int end_i = timeToIndexHead(endTime);
    vector<glm::vec2> posns;
    for (int i=start_i; i<end_i; ++i) {
        const HeadData& head = m_HeadData[i];
        posns.push_back(glm::vec2(head.getPos().x, head.getPos().z));
    }
//    vector<glm::vec2> posns = simplifyPath(origPosns, 0.1f);

    float dist = 0.0f;
    glm::vec2 pos = posns[0];
    glm::vec2 oldPos;
    for (int i=1; i<posns.size(); ++i) {
        oldPos = pos;
        pos = posns[i];
        dist += glm::distance(pos, oldPos);
    }
    return dist;
}

float User::getAvgDistFromWall(float startTime, float endTime) const
{
    int start_i = timeToIndexHead(startTime);
    int end_i = timeToIndexHead(endTime);
    float sum = 0;
    for (int i=start_i; i<end_i; ++i) {
        sum += m_HeadData[i].getPos().z;
    }
    return sum/(end_i-start_i);
}



vector<Touch> User::getTouches(float startTime, float endTime) const
{
    vector<Touch> touches;
    for (auto touch: m_Touches) {
        if (startTime <= touch.getTime() && touch.getTime() <= endTime) {
            touches.push_back(touch);
        }
    }
    return touches;
}

vector<Touch> User::getDeviceTouches(float startTime, float endTime) const
{
    vector<Touch> touches;
    for (auto touch: m_DeviceTouches) {
        if (startTime <= touch.getTime() && touch.getTime() <= endTime) {
            touches.push_back(touch);
        }
    }
    return touches;
}

vector<DeviceEntry> User::getDeviceEntries(float startTime, float endTime) const
{
    vector<DeviceEntry> deviceEntries;
    int start_i = timeToIndexDevice(startTime);
    int end_i = timeToIndexDevice(endTime);
    for (int i=start_i; i<end_i; ++i) {
        deviceEntries.push_back(m_DeviceEntries[i]);
    }
    return deviceEntries;
}

vector<glm::vec2> User::getHeadXZPosns(float startTime, float endTime) const
{
    vector<glm::vec2> posns;
    int start_i = timeToIndexHead(startTime);
    int end_i = timeToIndexHead(endTime);
    for (int i=start_i; i<end_i; ++i) {
        const glm::vec3 pos = m_HeadData[i].getPos();
        posns.push_back(glm::vec2(pos.x, pos.z));
    }
    return posns;
}

std::vector<glm::vec2> User::getDeviceXZSpacePosns(float startTime, float endTime) const
{
    vector<glm::vec2> posns;
    int start_i = timeToIndexDevice(startTime);
    int end_i = timeToIndexDevice(endTime);
    for (int i=start_i; i<end_i; ++i) {
        const glm::vec3 pos = m_DeviceEntries[i].getSpacePos();
        posns.push_back(glm::vec2(pos.x, pos.z));
    }
    return posns;
}

vector<glm::vec2> User::getHeadViewpoints(float startTime, float endTime) const
{
    vector<glm::vec2> viewpts;
    int start_i = timeToIndexHead(startTime);
    int end_i = timeToIndexHead(endTime);
    for (int i=start_i; i<end_i; ++i) {
        viewpts.push_back(m_HeadData[i].getWallViewpoint());
    }
    return viewpts;

}

int User::timeToIndexHead(float time) const
{
    return int(time * m_HeadData.size() / m_Duration);
}

int User::timeToIndexDevice(float time) const
{
    return int(time * m_DeviceEntries.size() / m_Duration);
}

float User::mapValues(float value, float fromMin, float fromMax, float toMin, float toMax) const
{
    float oldRange = fromMax - fromMin;
    float newRange = toMax - toMin;
    value = (value - fromMin) * newRange / oldRange + toMin;
    return value;
}

vector<glm::vec2> User::getHeadXZPosnsMapped(float startTime, float endTime, const glm::vec2 fromRangeMin, const glm::vec2 fromRangeMax, const glm::vec2 toRangeMin, const glm::vec2 toRangeMax) const
{
    vector<glm::vec2> posns;
    int start_i = timeToIndexHead(startTime);
    int end_i = timeToIndexHead(endTime);
    for (int i=start_i; i<end_i; ++i) {
        const glm::vec3 pos = m_HeadData[i].getPos();
        const glm::vec2 mappedPos = glm::vec2(
            mapValues(pos.x, fromRangeMin.x, fromRangeMax.x, toRangeMin.x, toRangeMax.x),
            mapValues(pos.z, fromRangeMin.y, fromRangeMax.y, toRangeMin.y, toRangeMax.y)
        );
        posns.push_back(mappedPos);
    }
    return posns;
}

vector<glm::vec2> User::getDeviceXZSpacePosnsMapped(float startTime, float endTime, const glm::vec2 fromRangeMin, const glm::vec2 fromRangeMax, const glm::vec2 toRangeMin, const glm::vec2 toRangeMax) const
{
    vector<glm::vec2> posns;
    int start_i = timeToIndexDevice(startTime);
    int end_i = timeToIndexDevice(endTime);
    for (int i=start_i; i<end_i; ++i) {
        const glm::vec3 pos = m_DeviceEntries[i].getSpacePos();
        const glm::vec2 mappedPos = glm::vec2(
            mapValues(pos.x, fromRangeMin.x, fromRangeMax.x, toRangeMin.x, toRangeMax.x),
            mapValues(pos.z, fromRangeMin.y, fromRangeMax.y, toRangeMin.y, toRangeMax.y)
        );
        posns.push_back(mappedPos);
    }
    return posns;
}
