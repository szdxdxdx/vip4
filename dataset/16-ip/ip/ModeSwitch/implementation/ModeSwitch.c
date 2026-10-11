#include "ModeSwitch.h"

void SAMSubModeDamp(ModeSwitch *this);
void SAMSubModePitch(ModeSwitch *this);
void SAMSubModeRoll(ModeSwitch *this);
void SAMSubModeCruise(ModeSwitch *this);

void ModeSwitchFun(void *p) {
    ModeSwitch *pIp = (ModeSwitch *)p;

    /* 进行模式切换流程 */
    switch (pIp->m_workMode) {
    case SAM_DAMP:
        SAMSubModeDamp(pIp);
        break;
    case SAM_PITCH:
        SAMSubModePitch(pIp);
        break;
    case SAM_ROLL:
        SAMSubModeRoll(pIp);
        break;
    case SAM_CRUISE:
        break;
    default:
        break;
    }
    return;
}

void SAMSubModeDamp(ModeSwitch *this) {
    float32 fabsmax; /* 临时：绝对值最大 */

    fabsmax = TripleFabsMax(this->pGyroRate[0], this->pGyroRate[1], this->pGyroRate[2]); /* 求三轴姿态角速度最大值 */

    if (fabsmax < 0.15f) { /* 三轴姿态角速度均小于0.15度/秒 */
        this->m_countPublic++; /* 方式计数器 */
    }

    /* 若700Ts角速度都小于0.07度/s 或速率阻尼持续时间大于128秒时,置俯仰角速度偏置为-0.5度/s, 转入俯仰搜索 */
    if ((this->m_countPublic > this->time_D2P) ||
        (this->m_countMode > this->time_D2P_overtime)) {
        this->m_workMode = SAM_PITCH;

        this->m_countMode = 0;   /* 清控制周期计数器 */
        this->m_countPublic = 0; /* 方式计数器 */
    }
    return;
}

void SAMSubModePitch(ModeSwitch *this) {
    float32 pirawtmp;
    if (this->flgSP == TRUE) { /* 若SP标志为见太阳 */
        pirawtmp = ABS(this->piyaw);

        if (pirawtmp > 0.25f) { /* 太敏俯仰测量角 > 0.25度 */
            this->m_countPublic++; /* 方式计数器 */

            if (this->m_countPublic > 12) { /* 持续12TS,则太阳搜索完成,转巡航 */
                /* 转入SAM巡航方式 */
                this->m_workMode = SAM_CRUISE; /* 置巡航方式字 */
                this->m_countMode = 0;         /* 清控制周期计数 */
                this->m_countPublic = 0;       /* 方式计数器 */
            }
        }
    } else {
        this->m_countPublic = 0; /* 方式计数器 */
    }

    if (this->m_countMode > 4500) { /* 若720秒太阳仍不出现,置ωx=0.5度/秒,ωy=0度/秒,转滚动搜索 */
        this->m_workMode = SAM_ROLL; /* 转入SAM滚动搜索方式 */
        this->m_countMode = 0;       /* 控制周期计数器 */
        this->m_countPublic = 0;     /* 方式计数器 */
    }
    return;
}

void SAMSubModeRoll(ModeSwitch *this) {
    float32 tmproyaw;

    if (this->flgSP == TRUE) { /* 若SP=1 */
        tmproyaw = ABS(this->royaw);

        if (tmproyaw > 1.0f) { /* 限幅 */
            this->m_countPublic++; /* 方式计数器计数 */

            if (this->m_countPublic > 12) { /* 方式计数器13=2.08s 〉2.048s */
                this->m_workMode = SAM_CRUISE;
                this->m_countMode = 0;   /* 控制周期计数器 */
                this->m_countPublic = 0; /* 方式计数器清零 */
            }
        }
    } else {
        this->m_countPublic = 0; /* 方式计数器清零 */
    }

    if (this->m_countMode > 5000) { /* 若800s太阳仍不出现,置ωx=0度/秒,ωy=-0.5度/秒,重新俯仰搜索 */
        this->m_workMode = SAM_PITCH;
        this->m_countMode = 0;   /* 控制周期计数器 */
        this->m_countPublic = 0; /* 方式计数器清零 */
    }
    return;
}

void SAMSubModeCruise(ModeSwitch *this) { return; }
