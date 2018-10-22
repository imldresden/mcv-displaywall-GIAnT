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

#ifndef _User_H_
#define _User_H_

#include <api.h>

#include <base/GLMHelper.h>
#include <string>

#include "HeadData.h"

class Touch
{
public:
    Touch(int userid, const glm::vec2& pos, float time, float duration, bool injected, std::string type);

    const glm::vec2& getPos() const;
    float getTime() const;
    float getDuration() const;
    bool getInjected() const;
    std::string getTType() const;

private:
    int m_UserID;
    glm::vec2 m_Pos;
    float m_Time;
    float m_Duration;
    bool m_Injected;
    std::string m_Type;
};

class DeviceEntry
{
public:
    DeviceEntry(int userid, const glm::vec2& screenPos, const glm::vec3& spacePos, const glm::vec3& orientation, double time);

    const int getUserID() const;
    void setWallViewpoint(const glm::vec2& pt);
    const glm::vec2& getWallViewpoint() const;
    const glm::vec2& getScreenPos() const;
    const glm::vec3& getSpacePos() const;
    const glm::vec3& getOrientation() const;
    double getTime() const;

private:
    int m_UserID;
    glm::vec2 m_ScreenPos;
    glm::vec3 m_SpacePos;
    glm::vec3 m_Orientation;
    glm::vec2 m_WallViewpoint;
    double m_Time;
};

class User
{
public:
    User(int userid, float duration);
    virtual ~User();

    void addHeadData(const HeadData& head);
    void addTouch(const Touch& touch);
    void addDeviceTouch(const Touch& touch);
    void addDeviceEntry(const DeviceEntry& deviceEntry);

    int getUserID() const;
    const int getHeadInfoCount() const;
    const int getDeviceEntryInfoCount() const;

    const glm::vec3& getHeadPos(float time) const;
    const glm::vec2& getWallViewpoint(float time) const;
    const glm::vec2& getDeviceWallViewpoint(float time) const;
    const glm::vec3& getHeadRot(float time) const;
    const HeadData getHeadData(float time) const;
    const DeviceEntry getDeviceEntry(float time) const;

    glm::vec3 getHeadPosAvg(float time, int smoothness) const;
    float getDistTravelled(float startTime, float endTime) const;
    float getAvgDistFromWall(float startTime, float endTime) const;

    std::vector<Touch> getTouches(float startTime, float endTime) const;
    std::vector<Touch> getDeviceTouches(float startTime, float endTime) const;
    std::vector<DeviceEntry> getDeviceEntries(float startTime, float endTime) const;
    std::vector<glm::vec2> getHeadXZPosns(float startTime, float endTime) const;
    std::vector<glm::vec2> getDeviceXZSpacePosns(float startTime, float endTime) const;
    std::vector<glm::vec2> getHeadViewpoints(float startTime, float endTime) const;
    std::vector<glm::vec2> getHeadXZPosnsMapped(float startTime, float endTime, const glm::vec2 fromRangeMin, const glm::vec2 fromRangeMax, const glm::vec2 toRangeMin, const glm::vec2 toRangeMax) const;
    std::vector<glm::vec2> getDeviceXZSpacePosnsMapped(float startTime, float endTime, const glm::vec2 fromRangeMin, const glm::vec2 fromRangeMax, const glm::vec2 toRangeMin, const glm::vec2 toRangeMax) const;

private:
    int timeToIndexHead(float time) const;
    int timeToIndexDevice(float time) const;
    float mapValues(float value, float fromMin, float fromMax, float toMin, float toMax) const;

    int m_UserID;
    float m_Duration;

    std::vector<HeadData> m_HeadData;
    std::vector<Touch> m_Touches;
    std::vector<Touch> m_DeviceTouches;
    std::vector<DeviceEntry> m_DeviceEntries;
};

#endif


