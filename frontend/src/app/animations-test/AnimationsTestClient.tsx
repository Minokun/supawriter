'use client';

import { useState } from 'react';
import MainLayout from '@/components/layout/MainLayout';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import Modal from '@/components/ui/Modal';
import Input from '@/components/ui/Input';
import { SkeletonCard } from '@/components/ui/Skeleton';
import { LoadingDots } from '@/components/ui/LoadingDots';

export default function AnimationsTestClient() {
  const [showModal, setShowModal] = useState(false);
  const [inputError, setInputError] = useState(false);

  return (
    <MainLayout>
      <div className="max-w-4xl mx-auto">
        <h1 className="font-heading text-3xl font-semibold text-text-primary mb-8">
          前端交互动画测试
        </h1>

        <section className="mb-12">
          <h2 className="font-heading text-xl font-semibold mb-4">按钮动画</h2>
          <div className="flex flex-wrap gap-4">
            <Button variant="primary">Primary 按钮</Button>
            <Button variant="secondary">Secondary 按钮</Button>
            <Button variant="cta">CTA 按钮</Button>
            <Button variant="text">Text 按钮</Button>
          </div>
        </section>

        <section className="mb-12">
          <h2 className="font-heading text-xl font-semibold mb-4">卡片悬停动画</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card hoverable>
              <h3 className="font-heading text-lg font-semibold mb-2">悬停我</h3>
              <p className="text-text-secondary">应该看到缩放和阴影效果</p>
            </Card>
            <Card hoverable>
              <h3 className="font-heading text-lg font-semibold mb-2">我也可以</h3>
              <p className="text-text-secondary">hover 时的边框颜色变化</p>
            </Card>
          </div>
        </section>

        <section className="mb-12">
          <h2 className="font-heading text-xl font-semibold mb-4">模态框动画</h2>
          <Button onClick={() => setShowModal(true)}>打开模态框</Button>
          <Modal
            isOpen={showModal}
            onClose={() => setShowModal(false)}
            title="测试模态框"
            message="这个模态框应该有淡入缩放效果"
          />
        </section>

        <section className="mb-12">
          <h2 className="font-heading text-xl font-semibold mb-4">输入框错误动画</h2>
          <div className="max-w-md">
            <Input
              placeholder="点击按钮测试错误抖动"
              error={inputError ? 'error' : undefined}
              errorMessage="这是一个错误提示"
            />
            <Button
              className="mt-4"
              onClick={() => {
                setInputError(true);
                setTimeout(() => setInputError(false), 500);
              }}
            >
              触发错误抖动
            </Button>
          </div>
        </section>

        <section className="mb-12">
          <h2 className="font-heading text-xl font-semibold mb-4">骨架屏动画</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <SkeletonCard />
            <SkeletonCard />
          </div>
        </section>

        <section className="mb-12">
          <h2 className="font-heading text-xl font-semibold mb-4">加载点动画</h2>
          <div className="flex items-center gap-8">
            <div>
              <p className="text-sm text-text-secondary mb-2">小</p>
              <LoadingDots size="sm" />
            </div>
            <div>
              <p className="text-sm text-text-secondary mb-2">中</p>
              <LoadingDots size="md" />
            </div>
            <div>
              <p className="text-sm text-text-secondary mb-2">大</p>
              <LoadingDots size="lg" />
            </div>
          </div>
        </section>
      </div>
    </MainLayout>
  );
}
