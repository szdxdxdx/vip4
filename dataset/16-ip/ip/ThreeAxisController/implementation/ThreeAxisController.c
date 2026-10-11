#include "ThreeAxisController.h"

void LimitControllerInput(ThreeAxisController *this);

void ThreeAxisControllerFun(void *p) {
    ThreeAxisController *pIp = (ThreeAxisController *)p;

    switch (pIp->workMode) {
    case SAM_DAMP:
        /* 速率阻尼 */
        pIp->destRate[0] = 0.0f; /* 滚动角目标角速度0 */
        pIp->destRate[1] = 0.0f; /* 俯仰角目标角速度0 */
        break;
    case SAM_PITCH:
        /* 俯仰搜索 */
        pIp->destRate[0] = 0.0f;  /* 滚动角目标角速度0 */
        pIp->destRate[1] = -0.5f; /* 俯仰角目标角速度-0.5 */
        break;
    case SAM_ROLL:
        /* 滚动搜索 */
        pIp->destRate[0] = 0.5f; /* 滚动角目标角速度0.5 */
        pIp->destRate[1] = 0.0f; /* 俯仰角目标角速度0 */
        break;
    case SAM_CRUISE:
        /* 巡航模式 */
        pIp->destRate[0] = 0.0f; /* 滚动角目标角速度0 */
        pIp->destRate[1] = 0.0f; /* 俯仰角目标角速度0 */
    default:
        break;
    }

    LimitControllerInput(pIp);

    /* 三轴控制器计算 */
    pIp->mController[0].fy = pIp->mController[0].Up * pIp->CTRL_PARAM_SAM[0].Kp + pIp->mController[0].Ud * pIp->CTRL_PARAM_SAM[0].Kd;
    pIp->mController[1].fy = pIp->mController[1].Up * pIp->CTRL_PARAM_SAM[1].Kp + pIp->mController[1].Ud * pIp->CTRL_PARAM_SAM[1].Kd;
    pIp->mController[2].fy = pIp->mController[2].Ud * pIp->CTRL_PARAM_SAM[2].Kd;

    /* 控制器输出限幅,伪速率调制器输入,即控制器输出 */
    pIp->u[0] = LimitFloat32(pIp->mController[0].fy, 1.3f); /* 伪速率状态量 */
    pIp->u[1] = LimitFloat32(pIp->mController[1].fy, 1.3f); /* 伪速率状态量 */
    pIp->u[2] = LimitFloat32(pIp->mController[2].fy, 1.3f); /* 伪速率状态量 */

    return;
}

void LimitControllerInput(ThreeAxisController *this) {
    /* 在进行控制器计算前,对输入信号进行限幅 */
    this->mController[0].Up = this->pAngle[0]; /* 角度减偏置量，偏置量为0  */
    this->mController[1].Up = this->pAngle[1]; /* 角度减偏置量，偏置量为0  */
    this->mController[2].Up = 0.0f;            /* Z轴角度清零 */

    this->mController[0].Ud = this->pRate[0] - this->destRate[0]; /* 角速度减偏置量 */
    this->mController[1].Ud = this->pRate[1] - this->destRate[1];   /* 角速度减偏置量 */
    this->mController[2].Ud = this->pRate[2]; /* Z轴角速度无偏置 */

    this->mController[0].Up = LimitFloat32(this->mController[0].Up, 8.0f); /* 角度限幅8° */
    this->mController[1].Up = LimitFloat32(this->mController[1].Up, 8.0f);

    this->mController[0].Ud = LimitFloat32(this->mController[0].Ud, 1.2f); /* 角速度限幅1.2° */
    this->mController[1].Ud = LimitFloat32(this->mController[1].Ud, 1.2f);
    this->mController[2].Ud = LimitFloat32(this->mController[2].Ud, 1.2f);
    return;
}
