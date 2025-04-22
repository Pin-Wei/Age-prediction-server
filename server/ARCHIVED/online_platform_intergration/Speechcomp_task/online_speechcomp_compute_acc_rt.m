% Compute accuracy and RT for online speechcomp
% 2022/11/4

clear

dataDir='C:\Users\quanta\TCNL Dropbox\tcnl tcnl\Tests\online\speechcomprehension_2022.2.4\data\';
outputDir='C:\Users\quanta\Dropbox\analysis\language\online_speechcomp\';

% Get file list
d=dir(fullfile(dataDir,'*.csv'));
l={d.name};

SUMMARY(length(l)).ID='';
for i=1:length(l)
    % Get subject ID
    c=strsplit(l{i},'_');
    id=c{1};
    
    % Read table
    t=readtable(fullfile(d(1).folder,l{i}));
    
    % Get condition index
    act=contains(t.condition,'action');
    obj=contains(t.condition,'object');
    pas=contains(t.condition,'passive');
    
    SUMMARY(i).ID=id;
    SUMMARY(i).ACTION_ACCURACY=sum(t.stim_resp_corr(act))*100/sum(act);
    SUMMARY(i).OBJECT_ACCURACY=sum(t.stim_resp_corr(obj))*100/sum(obj);
    SUMMARY(i).PASSIVE_ACCURACY=sum(t.stim_resp_corr(pas))*100/sum(pas);
    SUMMARY(i).ACTION_RT=mean(t.duration(act==1&t.stim_resp_corr==1));
    SUMMARY(i).OBJECT_RT=mean(t.duration(obj==1&t.stim_resp_corr==1));
    SUMMARY(i).PASSIVE_RT=mean(t.duration(pas==1&t.stim_resp_corr==1));
end
t2=struct2table(SUMMARY);
writetable(t2,fullfile(outputDir,'summary_online_speechcomp.csv'))
disp('Done.')