class Solution:
    def twoSum(self,nums, target: int):
        copy_list=nums
        for i in range(len(nums)-1):
            del copy_list[i]
            for k in range(len(copy_list) - 1):
                if nums[i] + copy_list[k] == target:
                    print([i,k])
Solution.twoSum(self=1,nums=[1,2,4.7],target=3)